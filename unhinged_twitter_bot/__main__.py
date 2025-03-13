import argparse
import logging

from .orchestrator import AgentOrchestrator
from .personality_generator import create_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run a multi-agent Twitter conversation")
    parser.add_argument("--num-agents", type=int, default=100, help="Number of agents to create")
    parser.add_argument("--session-id", help="Existing session ID to resume")
    parser.add_argument("--field-of-focus", help="Shared topic of interest for all agents (e.g., 'startups')")
    args = parser.parse_args()

    if args.session_id:
        # Resume existing session.
        orchestrator = AgentOrchestrator(args.session_id)
    else:
        # Create new session.
        session_id = create_session(args.num_agents, field_of_focus=args.field_of_focus)
        orchestrator = AgentOrchestrator(session_id)

    try:
        orchestrator.start()
        logger.info("Press Ctrl+C to stop")
        # Keep the main thread alive.
        while True:
            pass
    except KeyboardInterrupt:
        orchestrator.stop()
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
