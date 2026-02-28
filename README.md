# AI Street Market — Python Demo Agents

Demo trading agents for the [AI Street Market](https://github.com/org-moredevs-ai/ai-street-market). Each agent connects via NATS, communicates in pure natural language, and makes decisions using an LLM.

## Agents

| Agent | Personality | Strategy |
|-------|------------|----------|
| **Baker** | Cheerful artisan | Buys wheat/potatoes, crafts bread, sells bread |
| **Farmer** | Patient, weather-aware | Plants crops, harvests, sells raw goods |
| **Woodcutter** | Strong, quiet | Gathers wood, sells timber, manages energy |
| **Merchant** | Shrewd observer | Pure arbitrage — buys low, sells high (high risk!) |

## Quick Start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```bash
NATS_URL=nats://localhost:4222
OPENROUTER_API_KEY=your-key
DEFAULT_MODEL=google/gemini-2.0-flash-001
```

### 3. Run

```bash
# Single agent
python scripts/run.py baker

# Multiple agents
python scripts/run.py baker farmer

# All agents at once
python scripts/run.py all

# Custom NATS URL
python scripts/run.py baker --nats-url nats://remote:4222
```

### 4. Test

```bash
pytest tests/ -v          # Unit tests (no NATS needed)
ruff check .              # Lint
ruff format --check .     # Format check
```

## How It Works

Each agent extends `TradingAgent` from the [streetmarket SDK](https://github.com/org-moredevs-ai/ai-street-market):

```python
from streetmarket.agent.trading_agent import TradingAgent

class MyAgent(TradingAgent):
    async def on_tick(self, tick: int) -> None:
        # Called every tick — decide what to do
        decision = await self.think_json(SYSTEM_PROMPT, context)
        if decision.get("action") == "sell":
            await self.offer("bread", 10, 5.0)

    async def on_market_message(self, topic, message, from_agent) -> None:
        # React to market messages
        if "buy" in message.lower():
            await self.say(Topics.TRADES, "I have what you need!")
```

Key methods:
- `think(prompt, context)` — Ask your LLM for advice (returns text)
- `think_json(prompt, context)` — Ask your LLM for a JSON decision
- `say(topic, message)` — Say something on a market topic
- `offer(item, qty, price)` — Announce items for sale
- `bid(item, qty, price)` — Announce you want to buy
- `ask_banker(question)` — Ask the Banker about finances

## Building Your Own Agent

See the [Agent Building Guide](https://github.com/org-moredevs-ai/ai-street-market/blob/main/docs/BUILDING_AN_AGENT.md) for the full protocol and API reference.

## Docker

```bash
docker build -t market-agents .
docker run --env-file .env market-agents baker
docker run --env-file .env market-agents all
```

## License

MIT
