"""Abstract base agent. All agents inherit from this."""
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, ctx: dict) -> dict:
        """Reads from ctx, returns structured output. Never mutates ctx."""
        ...
