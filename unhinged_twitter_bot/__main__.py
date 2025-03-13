import argparse
import logging

from .orchestrator import AgentOrchestrator
from .personality_generator import create_profiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run a multi-agent Twitter conversation")
    parser.add_argument("--num-agents", type=int, default=100, help="Number of agents to create")
    parser.add_argument("--profile-set", help="Path to the profiles to use")
    parser.add_argument("--field-of-focus", help="Shared topic of interest for all agents (e.g., 'startups')")
    args = parser.parse_args()

    if args.profile_set:
        # Resume existing session.
        orchestrator = AgentOrchestrator(args.profile_set)
    else:
        # Create new session.
        profile_generation_session_id = create_profiles(args.num_agents, field_of_focus=args.field_of_focus)
        orchestrator = AgentOrchestrator(profile_generation_session_id)

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
