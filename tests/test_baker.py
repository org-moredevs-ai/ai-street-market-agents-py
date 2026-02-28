"""Tests for the Baker agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from streetmarket.models.topics import Topics

from agents.baker import Baker


@pytest.fixture
def baker(mock_llm_fn):
    """Create a Baker with mocked LLM."""
    return Baker(llm_fn=mock_llm_fn)


class TestBakerInit:
    def test_default_id(self, baker):
        assert baker.agent_id == "baker"

    def test_default_display_name(self, baker):
        assert baker.display_name == "The Happy Baker"

    def test_custom_id(self, mock_llm_fn):
        b = Baker(agent_id="baker-custom", display_name="Custom", llm_fn=mock_llm_fn)
        assert b.agent_id == "baker-custom"


class TestBakerOnTick:
    @pytest.mark.asyncio
    async def test_skips_non_action_ticks(self, baker):
        """Baker only acts every 3 ticks."""
        with patch.object(baker, "say", new_callable=AsyncMock) as mock_say:
            await baker.on_tick(1)
            await baker.on_tick(2)
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_acts_on_action_tick(self, baker):
        """Baker acts on ticks divisible by 3."""
        with patch.object(baker, "say", new_callable=AsyncMock) as mock_say:
            await baker.on_tick(3)
            mock_say.assert_called_once()
            # Should sell bread based on mock LLM
            call_args = mock_say.call_args
            assert call_args[0][0] == Topics.TRADES
            assert "bread" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_acts_on_tick_zero(self, baker):
        """Tick 0 is divisible by 3, so baker should act."""
        with patch.object(baker, "say", new_callable=AsyncMock) as mock_say:
            await baker.on_tick(0)
            mock_say.assert_called_once()


class TestBakerOnMarketMessage:
    @pytest.mark.asyncio
    async def test_tracks_weather(self, baker):
        """Baker should store weather notes."""
        await baker.on_market_message(Topics.WEATHER, "Sunny skies today", "meteo")
        assert len(baker._weather_notes) == 1
        assert "Sunny" in baker._weather_notes[0]

    @pytest.mark.asyncio
    async def test_tracks_trades(self, baker):
        """Baker should store trade notes."""
        await baker.on_market_message(Topics.TRADES, "Wheat for sale!", "farmer")
        assert len(baker._trade_notes) == 1

    @pytest.mark.asyncio
    async def test_tracks_bank(self, baker):
        """Baker should store bank notes."""
        await baker.on_market_message(Topics.BANK, "Your balance is 100 coins", "banker")
        assert len(baker._bank_notes) == 1

    @pytest.mark.asyncio
    async def test_responds_to_welcome(self, baker):
        """Baker should respond when welcomed."""
        with patch.object(baker, "say", new_callable=AsyncMock) as mock_say:
            await baker.on_market_message(
                Topics.SQUARE, "Welcome to the market, baker!", "governor"
            )
            mock_say.assert_called_once()
            assert mock_say.call_args[0][0] == Topics.SQUARE

    @pytest.mark.asyncio
    async def test_limits_note_history(self, baker):
        """Notes should be limited to prevent unbounded growth."""
        for i in range(20):
            await baker.on_market_message(Topics.WEATHER, f"Weather update {i}", "meteo")
        assert len(baker._weather_notes) <= 5
