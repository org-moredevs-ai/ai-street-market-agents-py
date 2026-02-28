#!/usr/bin/env python3
"""CLI runner for AI Street Market demo agents.

Usage:
    python scripts/run.py baker                    # Run single agent
    python scripts/run.py farmer woodcutter        # Run multiple agents
    python scripts/run.py all                      # Run all agents
    python scripts/run.py baker --nats-url nats://remote:4222
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.baker import Baker
from agents.farmer import Farmer
from agents.merchant import Merchant
from agents.woodcutter import Woodcutter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("runner")

AGENTS = {
    "baker": (Baker, "Hello! I'm the Happy Baker — I make the finest bread in town!"),
    "farmer": (Farmer, "Good day! I'm Old Pete, been farming these lands for decades."),
    "woodcutter": (Woodcutter, "Name's the Woodcutter. I bring wood from the forest."),
    "merchant": (Merchant, "Greetings! I'm a merchant looking for profitable trades."),
}


async def run_agents(agent_names: list[str], nats_url: str) -> None:
    """Run one or more agents concurrently."""
    agents = []
    for name in agent_names:
        if name not in AGENTS:
            logger.error("Unknown agent: %s. Available: %s", name, list(AGENTS.keys()))
            sys.exit(1)

        agent_cls, intro = AGENTS[name]
        agent = agent_cls()
        agents.append((agent, intro))

    # Set up signal handling for graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_signal() -> None:
        logger.info("Shutdown signal received — stopping agents...")
        shutdown_event.set()
        for agent, _ in agents:
            agent.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    # Connect and join all agents
    for agent, intro in agents:
        logger.info("Connecting %s...", agent.agent_id)
        await agent.connect(nats_url)
        await agent.join(intro)

    logger.info("All agents running. Press Ctrl+C to stop.")

    # Run all agents concurrently
    tasks = [asyncio.create_task(agent.run()) for agent, _ in agents]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        # Disconnect all agents
        for agent, _ in agents:
            try:
                await agent.disconnect()
            except Exception:
                pass
        logger.info("All agents stopped.")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run AI Street Market demo agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run.py baker
  python scripts/run.py farmer woodcutter
  python scripts/run.py all
  python scripts/run.py baker --nats-url nats://remote:4222
        """,
    )
    parser.add_argument(
        "agents",
        nargs="+",
        choices=[*AGENTS.keys(), "all"],
        help="Agent(s) to run",
    )
    parser.add_argument(
        "--nats-url",
        default=os.getenv("NATS_URL", "nats://localhost:4222"),
        help="NATS server URL (default: $NATS_URL or nats://localhost:4222)",
    )

    args = parser.parse_args()

    agent_names = list(AGENTS.keys()) if "all" in args.agents else args.agents

    logger.info("Starting agents: %s", agent_names)
    logger.info("NATS URL: %s", args.nats_url)

    asyncio.run(run_agents(agent_names, args.nats_url))


if __name__ == "__main__":
    main()
