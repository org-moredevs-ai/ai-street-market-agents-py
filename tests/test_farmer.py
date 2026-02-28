"""Tests for the Farmer agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from streetmarket.models.topics import Topics

from agents.farmer import Farmer


@pytest.fixture
def farmer(mock_llm_fn):
    """Create a Farmer with mocked LLM."""
    return Farmer(llm_fn=mock_llm_fn)


class TestFarmerInit:
    def test_default_id(self, farmer):
        assert farmer.agent_id == "farmer"

    def test_default_display_name(self, farmer):
        assert farmer.display_name == "Old Pete's Farm"


class TestFarmerOnTick:
    @pytest.mark.asyncio
    async def test_skips_non_action_ticks(self, farmer):
        """Farmer only acts every 4 ticks."""
        with patch.object(farmer, "say", new_callable=AsyncMock) as mock_say:
            await farmer.on_tick(1)
            await farmer.on_tick(2)
            await farmer.on_tick(3)
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_acts_on_action_tick(self, farmer):
        """Farmer acts on ticks divisible by 4."""
        sell_decision = {
            "action": "sell",
            "message": "Fresh wheat from the farm! 3 coins per bushel!",
        }
        with (
            patch.object(farmer, "think_json", new_callable=AsyncMock, return_value=sell_decision),
            patch.object(farmer, "say", new_callable=AsyncMock) as mock_say,
        ):
            await farmer.on_tick(4)
            mock_say.assert_called_once()
            call_args = mock_say.call_args
            assert call_args[0][0] == Topics.TRADES
            assert "wheat" in call_args[0][1].lower()


class TestFarmerOnMarketMessage:
    @pytest.mark.asyncio
    async def test_tracks_weather(self, farmer):
        """Farmer should store weather notes."""
        await farmer.on_market_message(Topics.WEATHER, "Rain expected tomorrow", "meteo")
        assert len(farmer._weather_notes) == 1

    @pytest.mark.asyncio
    async def test_reacts_to_storm(self, farmer):
        """Farmer should react urgently to storm warnings."""
        with patch.object(farmer, "say", new_callable=AsyncMock) as mock_say:
            await farmer.on_market_message(
                Topics.WEATHER, "A terrible storm is approaching!", "meteo"
            )
            mock_say.assert_called_once()
            assert mock_say.call_args[0][0] == Topics.SQUARE

    @pytest.mark.asyncio
    async def test_ignores_normal_weather(self, farmer):
        """Farmer should not react urgently to normal weather."""
        with patch.object(farmer, "say", new_callable=AsyncMock) as mock_say:
            await farmer.on_market_message(Topics.WEATHER, "Sunny and warm today", "meteo")
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_tracks_trades(self, farmer):
        """Farmer should store trade notes."""
        await farmer.on_market_message(Topics.TRADES, "Bread for sale!", "baker")
        assert len(farmer._trade_notes) == 1
