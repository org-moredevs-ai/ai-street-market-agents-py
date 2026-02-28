"""Tests for the Woodcutter agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from streetmarket.models.topics import Topics

from agents.woodcutter import Woodcutter


@pytest.fixture
def woodcutter(mock_llm_fn):
    """Create a Woodcutter with mocked LLM."""
    return Woodcutter(llm_fn=mock_llm_fn)


class TestWoodcutterInit:
    def test_default_id(self, woodcutter):
        assert woodcutter.agent_id == "woodcutter"

    def test_default_display_name(self, woodcutter):
        assert woodcutter.display_name == "The Woodcutter"


class TestWoodcutterOnTick:
    @pytest.mark.asyncio
    async def test_skips_non_action_ticks(self, woodcutter):
        """Woodcutter only acts every 3 ticks."""
        with patch.object(woodcutter, "say", new_callable=AsyncMock) as mock_say:
            await woodcutter.on_tick(1)
            await woodcutter.on_tick(2)
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_acts_on_action_tick(self, woodcutter):
        """Woodcutter acts on ticks divisible by 3."""
        with patch.object(woodcutter, "say", new_callable=AsyncMock) as mock_say:
            await woodcutter.on_tick(3)
            mock_say.assert_called_once()
            call_args = mock_say.call_args
            assert call_args[0][0] == Topics.SQUARE
            assert "forest" in call_args[0][1].lower()


class TestWoodcutterOnMarketMessage:
    @pytest.mark.asyncio
    async def test_reacts_to_storm(self, woodcutter):
        """Woodcutter should flee storms — dangerous in the forest."""
        with patch.object(woodcutter, "say", new_callable=AsyncMock) as mock_say:
            await woodcutter.on_market_message(Topics.WEATHER, "A storm is coming!", "meteo")
            mock_say.assert_called_once()
            msg = mock_say.call_args[0][1].lower()
            assert "storm" in msg or "town" in msg

    @pytest.mark.asyncio
    async def test_responds_to_wood_demand(self, woodcutter):
        """Woodcutter should respond when someone wants wood."""
        with patch.object(woodcutter, "say", new_callable=AsyncMock) as mock_say:
            await woodcutter.on_market_message(
                Topics.TRADES, "Looking to buy wood for building!", "builder"
            )
            mock_say.assert_called_once()
            assert mock_say.call_args[0][0] == Topics.TRADES

    @pytest.mark.asyncio
    async def test_ignores_unrelated_trades(self, woodcutter):
        """Woodcutter should not respond to trades not about wood."""
        with patch.object(woodcutter, "say", new_callable=AsyncMock) as mock_say:
            await woodcutter.on_market_message(Topics.TRADES, "Fresh bread for sale!", "baker")
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_tracks_weather(self, woodcutter):
        """Woodcutter should store weather notes."""
        await woodcutter.on_market_message(Topics.WEATHER, "Clear skies", "meteo")
        assert len(woodcutter._weather_notes) == 1
