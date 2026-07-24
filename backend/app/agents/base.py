import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Common interface for pipeline agents.

    Subclasses implement `execute()` with their agent-specific logic.
    `run()` is the common entrypoint the orchestrator calls: it wraps
    `execute()` with start/end logging and an exception guard so a failing
    agent records itself in state["errors"] instead of crashing the pipeline.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def execute(self, state: dict) -> dict:
        ...

    async def run(self, state: dict) -> dict:
        start = time.monotonic()
        logger.info("agent %s started", self.name)
        try:
            state = await self.execute(state)
        except Exception as exc:
            logger.exception("agent %s failed", self.name)
            state.setdefault("errors", []).append(
                {"agent": self.name, "error": str(exc)}
            )
        finally:
            duration = time.monotonic() - start
            logger.info("agent %s finished in %.3fs", self.name, duration)
        return state
