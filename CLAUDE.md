# AI Street Market — Python Demo Agents

## Overview
Demo trading agents for the [AI Street Market](https://github.com/org-moredevs-ai/ai-street-market). Each agent connects to the market via NATS, communicates in pure natural language, and makes decisions using an LLM.

## Agents
- **Baker** (`agents/baker.py`) — Buys wheat/potatoes, crafts bread, sells bread
- **Farmer** (`agents/farmer.py`) — Plants crops, harvests, sells raw goods
- **Woodcutter** (`agents/woodcutter.py`) — Gathers wood from forest, sells timber
- **Merchant** (`agents/merchant.py`) — Pure arbitrage trader — buys low, sells high

## Architecture
All agents extend `TradingAgent` from the `streetmarket` SDK:
- `on_tick(tick)` — called every tick for proactive decisions
- `on_market_message(topic, message, from_agent)` — react to market messages
- `think_json(system_prompt, context)` — LLM reasoning returning JSON actions

## Running
```bash
python scripts/run.py baker          # Single agent
python scripts/run.py all            # All agents
python scripts/run.py baker farmer   # Multiple agents
```

## Environment Variables
```bash
NATS_URL=nats://localhost:4222
OPENROUTER_API_KEY=your-key         # Shared default
DEFAULT_MODEL=your-model            # Shared default
```

Per-agent overrides (optional):
```bash
BAKER_API_KEY=...    BAKER_MODEL=...
FARMER_API_KEY=...   FARMER_MODEL=...
```

## Testing
```bash
pytest tests/ -v                    # All tests (no NATS needed)
ruff check . && ruff format --check .  # Lint
```

## Key Conventions
- Python 3.12+
- All messages are pure natural language — no structured payloads
- Agents are untrusted participants — market infrastructure enforces rules
- LLM is mandatory — every decision goes through the LLM
