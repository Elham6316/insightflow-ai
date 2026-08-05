import re

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pydantic import BaseModel

from app.agents.base import BaseAgent

MIN_COMPLETE_PERIODS = 4
FORECAST_HORIZON = 3
_ID_COLUMN_NAME_RE = re.compile(r"(^|_)id$", re.IGNORECASE)


class ForecastPoint(BaseModel):
    period: str
    predicted_value: float
    lower_bound: float
    upper_bound: float


class HistoryPoint(BaseModel):
    period: str
    value: float


def _pick_forecast_column(complete_periods: list[dict]) -> str | None:
    """Trend rows carry one sum_<col> per numeric column with no marked
    "primary" one, so pick whichever has the largest total magnitude across
    the complete periods, skipping id-like columns (their sum is meaningless
    to forecast). Same magnitude heuristic KpiAgent uses for its own
    column-picking fallback."""
    sum_keys = [k for k in complete_periods[0] if k.startswith("sum_")]
    best_key, best_total = None, None
    for key in sum_keys:
        if _ID_COLUMN_NAME_RE.search(key[len("sum_"):]):
            continue
        total = sum(abs(p[key]) for p in complete_periods if p.get(key) is not None)
        if best_total is None or total > best_total:
            best_key, best_total = key, total
    return best_key


def _future_period_labels(last_period: str, n: int) -> list[str]:
    start = pd.Period(last_period, freq="M")
    return [str(start + i) for i in range(1, n + 1)]


def _trim_to_recent_contiguous_block(periods: list[dict]) -> list[dict]:
    """EDAAgent already flags any period following a genuine gap (e.g. years
    of missing history) via gap_before_months (app/agents/eda.py). Fitting a
    regression across such a gap would treat it as one normal time step and
    silently corrupt the trend, so only train on the trailing block after
    the most recent flagged gap."""
    last_gap_idx = None
    for i, p in enumerate(periods):
        if p.get("gap_before_months"):
            last_gap_idx = i
    return periods[last_gap_idx:] if last_gap_idx is not None else periods


class ForecastAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "forecast"

    async def execute(self, state: dict) -> dict:
        if not state.get("has_time_series"):
            state["forecast"] = {
                "skipped": True,
                "reason": "Dataset has no usable time series.",
            }
            return state

        trends = (state.get("eda_results") or {}).get("trends") or {}
        periods = trends.get("data") or []
        complete_periods = [p for p in periods if not p.get("incomplete_period")]

        recent_periods = _trim_to_recent_contiguous_block(complete_periods)
        gap_excluded = len(complete_periods) - len(recent_periods)
        complete_periods = recent_periods

        if len(complete_periods) < MIN_COMPLETE_PERIODS:
            reason = (
                f"Not enough complete time periods (need at least "
                f"{MIN_COMPLETE_PERIODS}, found {len(complete_periods)})"
            )
            if gap_excluded:
                reason += (
                    f" after excluding {gap_excluded} earlier period(s) separated "
                    "from the recent data by a large gap"
                )
            state["forecast"] = {"skipped": True, "reason": reason}
            return state

        value_key = _pick_forecast_column(complete_periods)
        if value_key is None:
            state["forecast"] = {
                "skipped": True,
                "reason": "No numeric trend column available to forecast.",
            }
            return state

        y = np.array([p[value_key] for p in complete_periods], dtype=float)
        x = np.arange(len(y))

        model = sm.OLS(y, sm.add_constant(x)).fit()

        future_x = np.arange(len(y), len(y) + FORECAST_HORIZON)
        future_periods = _future_period_labels(complete_periods[-1]["period"], FORECAST_HORIZON)
        prediction = model.get_prediction(sm.add_constant(future_x, has_constant="add"))
        summary = prediction.summary_frame(alpha=0.05)

        forecast_points = [
            ForecastPoint(
                period=period,
                predicted_value=round(float(row["mean"]), 2),
                lower_bound=round(float(row["obs_ci_lower"]), 2),
                upper_bound=round(float(row["obs_ci_upper"]), 2),
            )
            for period, (_, row) in zip(future_periods, summary.iterrows())
        ]

        history = [
            HistoryPoint(period=p["period"], value=float(p[value_key])) for p in complete_periods
        ]

        caveat = (
            "This is a simple linear projection based on limited historical "
            "data, not a guarantee — treat it as a rough estimate."
        )
        if gap_excluded:
            caveat += (
                f" {gap_excluded} earlier period(s) before a large gap in the "
                "data were excluded so the projection isn't skewed by missing history."
            )

        state["forecast"] = {
            "skipped": False,
            "method": "linear_trend",
            "column": value_key[len("sum_"):],
            "history": [h.model_dump() for h in history],
            "forecast_points": [p.model_dump() for p in forecast_points],
            "caveat": caveat,
        }
        return state
