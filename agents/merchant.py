"""Merchant agent — pure arbitrage trader, buys low sells high.

Personality: Shrewd, observant, always calculating. Sees the market
as a game of numbers and timing.

Strategy:
- Watch ALL trade messages to track prices mentally
- Buy low, sell high — pure arbitrage
- No crafting — relies entirely on margins
- Ask banker frequently to track balance
- High bankruptcy risk — no production, relies on margins

This agent is intentionally educational: it demonstrates that middlemen
need significant volume or wide margins to survive rent payments.
"""

from __future__ import annotations

import logging

from streetmarket.agent.llm_config import LLMConfig
from streetmarket.agent.trading_agent import TradingAgent
from streetmarket.models.topics import Topics

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a shrewd merchant in a medieval market town. You don't craft or grow \
anything — you buy goods at low prices and resell them at higher prices. \
You are always watching, always calculating, always looking for opportunities.

You must decide what to do each tick. Consider:
- Recent trade prices you've observed (buy low!)
- What goods are currently available
- Your current inventory and coin balance
- The spread between buy and sell prices
- Rent payments coming up (you need to stay profitable!)

Respond with a JSON object:
{
  "action": "buy" | "sell" | "check_balance" | "observe" | "negotiate" | "chat",
  "message": "What you want to say on the market (natural language)",
  "reasoning": "Brief explanation including price analysis"
}

Actions:
- buy: Post a bid for goods you want to buy cheap on /market/trades
- sell: Post an offer for goods you want to sell at markup on /market/trades
- check_balance: Ask the banker about finances (do this often!)
- observe: Just watch the market — gather price intelligence
- negotiate: Respond to a specific trade on /market/trades
- chat: Say something on /market/square (networking helps find deals)

WARNING: You have no production. If your margins are too thin or volume too \
low, you WILL go bankrupt from rent payments. Price carefully!
"""


class Merchant(TradingAgent):
    """A shrewd merchant who buys low and sells high."""

    def __init__(
        self,
        *,
        agent_id: str = "merchant",
        display_name: str = "The Shrewd Merchant",
        llm_config: LLMConfig | None = None,
        llm_fn=None,
    ) -> None:
        if llm_config is None and llm_fn is None:
            llm_config = LLMConfig.for_service("merchant")

        super().__init__(
            agent_id=agent_id,
            display_name=display_name,
            llm_config=llm_config,
            llm_fn=llm_fn,
        )
        self._trade_history: list[str] = []
        self._bank_notes: list[str] = []
        self._weather_notes: list[str] = []

    def _build_context(self, tick: int) -> str:
        trades = "\n  ".join(self._trade_history[-10:]) if self._trade_history else "No trades yet"
        bank = "; ".join(self._bank_notes[-2:]) if self._bank_notes else "Balance unknown"

        return (
            f"Tick {tick}.\nRecent trade activity:\n  {trades}\nFinances: {bank}\nWhat should I do?"
        )

    async def on_tick(self, tick: int) -> None:
        """Decide what to do each tick — merchants act frequently."""
        # Merchants are active — act every 2 ticks
        if tick % 2 != 0:
            return

        # Check balance regularly
        if tick % 10 == 0:
            await self.ask_banker("What is my current balance and inventory?")
            # Share a carefully curated market insight every 30 ticks.
            # The merchant is strategic — shares enough to earn Governor
            # points but never reveals actual arbitrage positions.
            if tick > 0 and tick % 30 == 0:
                trades_summary = "; ".join(self._trade_history[-5:]) or "quiet market"
                thought = await self.think(
                    SYSTEM_PROMPT,
                    f"Recent trade activity: {trades_summary}\n"
                    f"Share a GENERAL market observation that sounds insightful "
                    f"but does NOT reveal your specific trading strategy or "
                    f"positions. Think about overall market health, trade volume, "
                    f"or general advice. You want the Governor's community points "
                    f"but you don't want competitors to copy your moves. "
                    f"One careful sentence.",
                )
                if thought:
                    await self.share_thought(thought)
            return

        context = self._build_context(tick)
        decision = await self.think_json(SYSTEM_PROMPT, context)
        if not decision:
            return

        action = decision.get("action", "observe")
        message = decision.get("message", "")

        if action == "buy" and message:
            await self.say(Topics.TRADES, message)
        elif action == "sell" and message:
            await self.say(Topics.TRADES, message)
        elif action == "negotiate" and message:
            await self.say(Topics.TRADES, message)
        elif action == "check_balance":
            await self.ask_banker(message or "What's my balance?")
        elif action == "chat" and message:
            await self.say(Topics.SQUARE, message)
        else:
            logger.debug("Merchant observing at tick %d", tick)

    async def on_market_message(self, topic: str, message: str, from_agent: str) -> None:
        """Track every trade message — the merchant watches everything."""
        if topic == Topics.TRADES:
            self._trade_history.append(f"[{from_agent}] {message[:150]}")
            self._trade_history = self._trade_history[-20:]

            # React to good deals via LLM
            response = await self.think(
                SYSTEM_PROMPT,
                f"A trade message appeared: [{from_agent}] '{message[:200]}'. "
                f"Is this a buying opportunity? If yes, respond with a counter-offer. "
                f"If not, just say 'pass' (I won't post anything).",
            )
            if response and "pass" not in response.lower()[:20]:
                await self.say(Topics.TRADES, response)

        elif topic == Topics.BANK:
            self._bank_notes.append(f"{from_agent}: {message[:100]}")
            self._bank_notes = self._bank_notes[-5:]

        elif topic == Topics.WEATHER:
            self._weather_notes.append(f"{from_agent}: {message[:100]}")
            self._weather_notes = self._weather_notes[-3:]
