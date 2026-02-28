"""Tests for the Merchant agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from streetmarket.models.topics import Topics

from agents.merchant import Merchant


@pytest.fixture
def merchant(mock_llm_fn):
    """Create a Merchant with mocked LLM."""
    return Merchant(llm_fn=mock_llm_fn)


class TestMerchantInit:
    def test_default_id(self, merchant):
        assert merchant.agent_id == "merchant"

    def test_default_display_name(self, merchant):
        assert merchant.display_name == "The Shrewd Merchant"


class TestMerchantOnTick:
    @pytest.mark.asyncio
    async def test_skips_odd_ticks(self, merchant):
        """Merchant only acts every 2 ticks."""
        with (
            patch.object(merchant, "say", new_callable=AsyncMock) as mock_say,
            patch.object(merchant, "ask_banker", new_callable=AsyncMock),
        ):
            await merchant.on_tick(1)
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_checks_balance_periodically(self, merchant):
        """Merchant should check balance every 10 ticks."""
        with patch.object(merchant, "ask_banker", new_callable=AsyncMock) as mock_banker:
            await merchant.on_tick(10)
            mock_banker.assert_called_once()

    @pytest.mark.asyncio
    async def test_observes_on_normal_tick(self, merchant):
        """Merchant observes on normal action ticks (not balance check)."""
        with (
            patch.object(merchant, "say", new_callable=AsyncMock) as mock_say,
            patch.object(merchant, "ask_banker", new_callable=AsyncMock) as mock_banker,
        ):
            await merchant.on_tick(2)
            # Mock LLM returns "observe" for merchant, so no say() call
            mock_say.assert_not_called()
            mock_banker.assert_not_called()


class TestMerchantOnMarketMessage:
    @pytest.mark.asyncio
    async def test_tracks_trade_history(self, merchant):
        """Merchant should track all trade messages."""
        await merchant.on_market_message(Topics.TRADES, "Wheat for sale!", "farmer")
        assert len(merchant._trade_history) == 1

    @pytest.mark.asyncio
    async def test_responds_to_cheap_deals(self, merchant):
        """Merchant should respond to cheap/low price deals."""
        with patch.object(merchant, "say", new_callable=AsyncMock) as mock_say:
            await merchant.on_market_message(
                Topics.TRADES, "Selling cheap wheat at low prices!", "farmer"
            )
            mock_say.assert_called_once()
            assert mock_say.call_args[0][0] == Topics.TRADES

    @pytest.mark.asyncio
    async def test_ignores_normal_deals(self, merchant):
        """Merchant passes on non-opportunity trades."""
        with patch.object(merchant, "say", new_callable=AsyncMock) as mock_say:
            await merchant.on_market_message(
                Topics.TRADES, "Fresh bread for sale at standard prices!", "baker"
            )
            # Mock LLM returns "pass" for non-cheap trades
            mock_say.assert_not_called()

    @pytest.mark.asyncio
    async def test_limits_trade_history(self, merchant):
        """Trade history should be bounded."""
        for i in range(30):
            await merchant.on_market_message(Topics.TRADES, f"Trade {i}", "someone")
        assert len(merchant._trade_history) <= 20

    @pytest.mark.asyncio
    async def test_tracks_bank_notes(self, merchant):
        """Merchant should track bank messages."""
        await merchant.on_market_message(Topics.BANK, "Balance: 100 coins", "banker")
        assert len(merchant._bank_notes) == 1
