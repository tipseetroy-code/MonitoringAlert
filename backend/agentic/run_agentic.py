#!/usr/bin/env python3
"""
Main entry point for Agentic SRE Copilot
Run as: python backend/agentic/run_agentic.py
Or via systemd service: sudo systemctl start sre-agent
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.agentic import initialize_orchestrator, get_orchestrator
from backend.agentic_config import get_orchestrator_config

# Configure logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/sre-agent/agentic.log"),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for agentic loop
    """
    logger.info("=" * 80)
    logger.info("SRE Agentic Copilot Starting")
    logger.info("=" * 80)

    # Verify required environment variables
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY not set - LLM reasoning will fail")
        logger.info("Set: export GOOGLE_API_KEY=your-key")

    # Load configuration
    try:
        config = get_orchestrator_config()
        logger.info(f"Configuration loaded: {len(config.get('apps', []))} apps to monitor")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Initialize orchestrator
    try:
        orchestrator = initialize_orchestrator(config)
        logger.info("Orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        sys.exit(1)

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        orchestrator.stop_monitoring()
        loop.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start monitoring loop
    try:
        monitoring_interval = config.get("monitoring_interval", 30)
        await orchestrator.run_monitoring_loop(interval_seconds=monitoring_interval)
    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("SRE Agentic Copilot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
