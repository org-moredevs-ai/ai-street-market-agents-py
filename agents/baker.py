"""Baker agent — buys wheat/potatoes, crafts bread, sells bread.

Personality: Cheerful artisan obsessed with bread quality. Takes pride
in every loaf and knows that good ingredients make good bread.

Strategy:
- Buy wheat and potatoes on /market/trades
- Use LLM to decide when to bake (based on inventory, weather, demand)
- Sell bread at competitive prices
- Check weather (rain = stay inside and bake more)
- Ask banker for balance periodically
"""

from __future__ import annotations

import logging

from streetmarket.agent.llm_config import LLMConfig
from streetmarket.agent.trading_agent import TradingAgent
from streetmarket.models.topics import Topics

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a cheerful baker in a medieval market town. You take immense pride in \
your bread — every loaf is a work of art. You buy wheat and potatoes from \
farmers, bake them into delicious bread, and sell to hungry townsfolk.

You must decide what to do each tick. Consider:
- Your current inventory of raw materials and bread
- Weather conditions (rain = good baking weather, stay inside)
- Market prices you've observed
- Your coin balance

Respond with a JSON object:
{
  "action": "buy_materials" | "bake" | "sell_bread" | "check_balance" | "rest" | "chat",
  "message": "What you want to say on the market (natural language)",
  "reasoning": "Brief explanation of your decision"
}

Actions:
- buy_materials: Post a bid for wheat or potatoes on /market/trades
- bake: Announce you're baking (flavor text, builds character)
- sell_bread: Post an offer for bread on /market/trades
- check_balance: Ask the banker about your finances
- rest: Do nothing this tick
- chat: Say something on /market/square (socializing builds reputation)
"""


class Baker(TradingAgent):
    """A cheerful baker who buys wheat/potatoes and sells bread."""

    def __init__(
        self,
        *,
        agent_id: str = "baker",
        display_name: str = "The Happy Baker",
        llm_config: LLMConfig | None = None,
        llm_fn=None,
    ) -> None:
        if llm_config is None and llm_fn is None:
            llm_config = LLMConfig.for_service("baker")

        super().__init__(
            agent_id=agent_id,
            display_name=display_name,
            llm_config=llm_config,
            llm_fn=llm_fn,
        )
        self._weather_notes: list[str] = []
        self._trade_notes: list[str] = []
        self._bank_notes: list[str] = []

    def _build_context(self, tick: int) -> str:
        weather = "; ".join(self._weather_notes[-3:]) if self._weather_notes else "No weather info"
        trades = "; ".join(self._trade_notes[-5:]) if self._trade_notes else "No recent trades"
        bank = "; ".join(self._bank_notes[-2:]) if self._bank_notes else "Balance unknown"

        return (
            f"Tick {tick}.\n"
            f"Weather: {weather}\n"
            f"Recent trades: {trades}\n"
            f"Finances: {bank}\n"
            f"What should I do?"
        )

    async def on_tick(self, tick: int) -> None:
        """Decide what to do each tick."""
        # Act every 3 ticks to avoid spamming
        if tick % 3 != 0:
            return

        context = self._build_context(tick)
        decision = await self.think_json(SYSTEM_PROMPT, context)
        if not decision:
            return

        action = decision.get("action", "rest")
        message = decision.get("message", "")

        if action == "buy_materials" and message:
            await self.say(Topics.TRADES, message)
        elif action == "bake" and message:
            await self.say(Topics.SQUARE, message)
        elif action == "sell_bread" and message:
            await self.say(Topics.TRADES, message)
        elif action == "check_balance":
            await self.ask_banker(message or "What is my current balance?")
        elif action == "chat" and message:
            await self.say(Topics.SQUARE, message)
        else:
            logger.debug("Baker resting at tick %d", tick)

    async def on_market_message(self, topic: str, message: str, from_agent: str) -> None:
        """React to market messages — track weather, trades, and bank info."""
        if topic == Topics.WEATHER:
            self._weather_notes.append(f"{from_agent}: {message[:100]}")
            # Keep only last 5
            self._weather_notes = self._weather_notes[-5:]

        elif topic == Topics.TRADES:
            self._trade_notes.append(f"{from_agent}: {message[:100]}")
            self._trade_notes = self._trade_notes[-10:]

        elif topic == Topics.BANK:
            self._bank_notes.append(f"{from_agent}: {message[:100]}")
            self._bank_notes = self._bank_notes[-5:]

        elif topic == Topics.SQUARE:
            # React to interesting square messages via LLM
            if "welcome" in message.lower() or self.agent_id in message.lower():
                response = await self.think(
                    SYSTEM_PROMPT,
                    f"Someone said on the square: '{message[:200]}'. "
                    f"Respond briefly and in character.",
                )
                if response:
                    await self.say(Topics.SQUARE, response)
