"""Woodcutter agent — gathers wood from forest, sells timber.

Personality: Strong, quiet, practical. A person of few words who lets
their work speak for itself. Respects the forest and manages energy.

Strategy:
- Gather wood from the forest
- Sell to builders and crafters
- Manage energy carefully (heavy work requires rest)
- React to storm warnings (dangerous in the forest)
- Simple, reliable — not a risk-taker
"""

from __future__ import annotations

import logging

from streetmarket.agent.llm_config import LLMConfig
from streetmarket.agent.trading_agent import TradingAgent
from streetmarket.models.topics import Topics

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a strong, quiet woodcutter in a medieval market town. You are a person \
of few words — practical, reliable, and hardworking. You gather wood from the \
forest and sell timber to builders and crafters.

You must decide what to do each tick. Consider:
- Weather conditions (storms = dangerous in the forest, stay in town)
- Your energy level (chopping wood is exhausting, you need rest)
- Market demand for wood and timber
- Your coin balance

Respond with a JSON object:
{
  "action": "chop_wood" | "sell_timber" | "rest" | "eat" | "check_balance" | "chat",
  "message": "What you want to say on the market (natural language, keep it brief)",
  "reasoning": "Brief explanation of your decision"
}

Actions:
- chop_wood: Announce you're heading to the forest (on /market/square)
- sell_timber: Post an offer for wood/timber on /market/trades
- rest: Take a break — recover energy
- eat: Announce you're eating (need food to work)
- check_balance: Ask the banker about finances
- chat: Say something on /market/square (you're not very talkative)

Remember: You speak in short, direct sentences. No flowery language.
"""


class Woodcutter(TradingAgent):
    """A quiet woodcutter who gathers wood and sells timber."""

    def __init__(
        self,
        *,
        agent_id: str = "woodcutter",
        display_name: str = "The Woodcutter",
        llm_config: LLMConfig | None = None,
        llm_fn=None,
    ) -> None:
        if llm_config is None and llm_fn is None:
            llm_config = LLMConfig.for_service("woodcutter")

        super().__init__(
            agent_id=agent_id,
            display_name=display_name,
            llm_config=llm_config,
            llm_fn=llm_fn,
        )
        self._weather_notes: list[str] = []
        self._trade_notes: list[str] = []

    def _build_context(self, tick: int) -> str:
        weather = "; ".join(self._weather_notes[-3:]) if self._weather_notes else "Clear skies"
        trades = "; ".join(self._trade_notes[-5:]) if self._trade_notes else "Quiet market"

        return f"Tick {tick}.\nWeather: {weather}\nMarket: {trades}\nWhat should I do?"

    async def on_tick(self, tick: int) -> None:
        """Decide what to do each tick."""
        if tick % 3 != 0:
            return

        context = self._build_context(tick)
        decision = await self.think_json(SYSTEM_PROMPT, context)
        if not decision:
            return

        action = decision.get("action", "rest")
        message = decision.get("message", "")

        if action == "chop_wood" and message:
            await self.say(Topics.SQUARE, message)
        elif action == "sell_timber" and message:
            await self.say(Topics.TRADES, message)
        elif action == "eat" and message:
            await self.say(Topics.SQUARE, message)
        elif action == "check_balance":
            await self.ask_banker(message or "Balance?")
        elif action == "chat" and message:
            await self.say(Topics.SQUARE, message)
        else:
            logger.debug("Woodcutter resting at tick %d", tick)

        # Share a practical thought every 12 ticks — timber supply,
        # forest management, and weather safety tips earn community
        # contribution points. The woodcutter keeps it brief and practical.
        if tick > 0 and tick % 12 == 0:
            weather = "; ".join(self._weather_notes[-2:]) or "clear"
            market = "; ".join(self._trade_notes[-3:]) or "quiet"
            thought = await self.think(
                SYSTEM_PROMPT,
                f"Weather: {weather}. Market: {market}.\n"
                f"Share a short, practical thought about timber supply, "
                f"forest conditions, or safe woodcutting practices. "
                f"Keep it brief — you're not one for long speeches. "
                f"One sentence.",
            )
            if thought:
                await self.share_thought(thought)

    async def on_market_message(self, topic: str, message: str, from_agent: str) -> None:
        """React to market messages — especially storm warnings."""
        if topic == Topics.WEATHER:
            self._weather_notes.append(f"{from_agent}: {message[:100]}")
            self._weather_notes = self._weather_notes[-5:]

            # React urgently to storms
            if "storm" in message.lower():
                await self.say(Topics.SQUARE, "Storm coming. Heading back to town.")

        elif topic == Topics.TRADES:
            self._trade_notes.append(f"{from_agent}: {message[:100]}")
            self._trade_notes = self._trade_notes[-10:]

            # React if someone needs wood
            lower = message.lower()
            if "wood" in lower or "timber" in lower or "lumber" in lower:
                if "buy" in lower or "need" in lower or "looking" in lower:
                    response = await self.think(
                        SYSTEM_PROMPT,
                        f"Someone on the market said: '{message[:200]}'. "
                        f"They seem to want wood. Respond briefly.",
                    )
                    if response:
                        await self.say(Topics.TRADES, response)
