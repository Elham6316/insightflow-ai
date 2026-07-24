import asyncio
import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.agents.base import BaseAgent
from app.services.llm_client import MODEL_NAME, client

logger = logging.getLogger(__name__)

DEFAULT_AGENTS_TO_RUN = ["data_quality", "eda", "insight"]

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class PlannerOutput(BaseModel):
    data_domain: Literal["sales", "tourism", "complaints", "finance", "generic"]
    has_time_series: bool
    reasoning: str
    agents_to_run: list[str]


FALLBACK_OUTPUT = PlannerOutput(
    data_domain="generic",
    has_time_series=False,
    reasoning="Fallback default: the LLM did not return valid JSON after retrying.",
    agents_to_run=DEFAULT_AGENTS_TO_RUN,
)


def _build_prompt(profile: dict) -> str:
    shape = profile.get("shape", {})
    columns = profile.get("columns", {})
    sample = profile.get("sample", [])

    return f"""You are a data analysis planner. Given a dataset profile, classify the \
data and decide which downstream agents should run.

Shape: {shape.get("rows", "?")} rows x {shape.get("columns", "?")} columns
Columns and dtypes: {json.dumps(columns)}
Sample rows: {json.dumps(sample)}

Return ONLY valid JSON, with no markdown fences and no commentary, matching exactly \
this shape:
{{
  "data_domain": "sales | tourism | complaints | finance | generic",
  "has_time_series": true/false,
  "reasoning": "short explanation",
  "agents_to_run": ["data_quality", "eda", "insight", ...]
}}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = _JSON_BLOCK_RE.search(text)
    if match:
        text = match.group(0)
    return json.loads(text)


class PlannerAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "planner"

    async def execute(self, state: dict) -> dict:
        profile = state.get("profile", {})
        prompt = _build_prompt(profile)

        output = await self._get_plan(prompt)

        state["data_domain"] = output.data_domain
        state["has_time_series"] = output.has_time_series
        state["reasoning"] = output.reasoning
        state["agents_to_run"] = output.agents_to_run
        state["planner_output"] = output.model_dump()
        return state

    async def _get_plan(self, prompt: str) -> PlannerOutput:
        attempts = 2
        for attempt in range(1, attempts + 1):
            raw = await asyncio.to_thread(self._call_llm, prompt)
            try:
                data = _extract_json(raw)
                return PlannerOutput.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "planner: malformed LLM output on attempt %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )

        logger.warning("planner: falling back to default plan after %d attempts", attempts)
        return FALLBACK_OUTPUT

    def _call_llm(self, prompt: str) -> str:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text
