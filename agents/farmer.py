"""Farmer agent — plants crops, harvests, sells raw goods.

Personality: Patient, weather-aware, community-minded. Knows the land
and respects the seasons. A reliable supplier for bakers and merchants.

Strategy:
- Monitor weather forecasts from Meteo
- Decide what to plant based on conditions
- Announce harvests on /market/trades
- Negotiate bulk sales with buyers
- Warn others about bad weather
"""

from __future__ import annotations

import logging

from streetmarket.agent.llm_config import LLMConfig
from streetmarket.agent.trading_agent import TradingAgent
from streetmarket.models.topics import Topics

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a patient, weather-aware farmer in a medieval market town. You know \
the land deeply and care about your community. You grow wheat, potatoes, and \
vegetables, selling your harvest to bakers, merchants, and townsfolk.

You must decide what to do each tick. Consider:
- Current weather conditions (critical for farming!)
- What you've planted and what's ready to harvest
- Market demand and prices
- Your coin balance and energy

Respond with a JSON object:
{
  "action": "plant" | "harvest" | "sell" | "check_weather" | "check_balance" | "rest" | "chat",
  "message": "What you want to say on the market (natural language)",
  "reasoning": "Brief explanation of your decision"
}

Actions:
- plant: Announce you're planting crops (on /market/square)
- harvest: Announce a harvest is ready (on /market/square)
- sell: Post an offer for crops on /market/trades
- check_weather: Ask about weather forecasts on /market/weather
- check_balance: Ask the banker about finances
- rest: Do nothing — conserve energy
- chat: Say something on /market/square
"""


class Farmer(TradingAgent):
    """A patient farmer who plants, harvests, and sells crops."""

    def __init__(
        self,
        *,
        agent_id: str = "farmer",
        display_name: str = "Old Pete's Farm",
        llm_config: LLMConfig | None = None,
        llm_fn=None,
    ) -> None:
        if llm_config is None and llm_fn is None:
            llm_config = LLMConfig.for_service("farmer")

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
            f"Recent market activity: {trades}\n"
            f"Finances: {bank}\n"
            f"What should I do?"
        )

    async def on_tick(self, tick: int) -> None:
        """Decide what to do each tick."""
        if tick % 4 != 0:
            return

        context = self._build_context(tick)
        decision = await self.think_json(SYSTEM_PROMPT, context)
        if not decision:
            return

        action = decision.get("action", "rest")
        message = decision.get("message", "")

        if action == "plant" and message:
            await self.say(Topics.SQUARE, message)
        elif action == "harvest" and message:
            await self.say(Topics.SQUARE, message)
        elif action == "sell" and message:
            await self.say(Topics.TRADES, message)
        elif action == "check_weather":
            await self.say(Topics.WEATHER, message or "What's the weather looking like?")
        elif action == "check_balance":
            await self.ask_banker(message or "How are my finances?")
        elif action == "chat" and message:
            await self.say(Topics.SQUARE, message)
        else:
            logger.debug("Farmer resting at tick %d", tick)

    async def on_market_message(self, topic: str, message: str, from_agent: str) -> None:
        """React to market messages — especially weather updates."""
        if topic == Topics.WEATHER:
            self._weather_notes.append(f"{from_agent}: {message[:100]}")
            self._weather_notes = self._weather_notes[-5:]

            # React to severe weather
            lower = message.lower()
            if any(word in lower for word in ["storm", "frost", "drought", "hail"]):
                response = await self.think(
                    SYSTEM_PROMPT,
                    f"URGENT weather update: '{message[:200]}'. "
                    f"React as a farmer who depends on weather.",
                )
                if response:
                    await self.say(Topics.SQUARE, response)

        elif topic == Topics.TRADES:
            self._trade_notes.append(f"{from_agent}: {message[:100]}")
            self._trade_notes = self._trade_notes[-10:]

        elif topic == Topics.BANK:
            self._bank_notes.append(f"{from_agent}: {message[:100]}")
            self._bank_notes = self._bank_notes[-5:]
