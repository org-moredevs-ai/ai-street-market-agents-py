"""Shared test fixtures — mock LLM and NATS for unit testing."""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_llm_fn() -> Callable[[str, str], Coroutine[Any, Any, str]]:
    """Create a mock LLM function that returns predictable JSON responses.

    The mock returns a JSON response based on keywords in the context:
    - Contains "tick" -> action based on agent type
    - Default -> rest action
    """

    async def _llm(system_prompt: str, context: str) -> str:
        # Detect agent type from system prompt
        lower_prompt = system_prompt.lower()
        lower_context = context.lower()

        if "baker" in lower_prompt:
            if "tick" in lower_context:
                return json.dumps(
                    {
                        "action": "sell_bread",
                        "message": "Fresh bread for sale! 5 coins per loaf!",
                        "reasoning": "Time to sell some bread.",
                    }
                )
            if "someone said" in lower_context or "welcome" in lower_context:
                return "Thank you kindly! Nothing like fresh bread!"
            return json.dumps({"action": "rest", "message": "", "reasoning": "Resting."})

        if "farmer" in lower_prompt:
            if "urgent" in lower_context or "storm" in lower_context:
                return "Better secure the crops! A storm is coming!"
            if "tick" in lower_context:
                return json.dumps(
                    {
                        "action": "sell",
                        "message": "Fresh wheat from the farm! 3 coins per bushel!",
                        "reasoning": "Harvest is in, time to sell.",
                    }
                )
            return json.dumps({"action": "rest", "message": "", "reasoning": "Resting."})

        if "woodcutter" in lower_prompt:
            if "wood" in lower_context or "timber" in lower_context:
                return "I've got timber. 4 coins per bundle."
            if "tick" in lower_context:
                return json.dumps(
                    {
                        "action": "chop_wood",
                        "message": "Heading to the forest.",
                        "reasoning": "Need more wood.",
                    }
                )
            return json.dumps({"action": "rest", "message": "", "reasoning": "Resting."})

        if "merchant" in lower_prompt:
            if "trade message" in lower_context:
                # Only respond to good deals
                if "cheap" in lower_context or "low" in lower_context:
                    return "I'll take that deal! Name your price."
                return "pass"
            if "tick" in lower_context:
                return json.dumps(
                    {
                        "action": "observe",
                        "message": "",
                        "reasoning": "Watching the market for opportunities.",
                    }
                )
            return json.dumps({"action": "observe", "message": "", "reasoning": "Observing."})

        return json.dumps({"action": "rest", "message": "", "reasoning": "Unknown agent."})

    return _llm


@pytest.fixture
def mock_nats_client() -> MagicMock:
    """Create a mock MarketBusClient."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.publish = AsyncMock()
    client.subscribe = AsyncMock()
    client.is_connected = True
    return client
