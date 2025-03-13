import logging
import threading
from pathlib import Path

import yaml

from .agent import Agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, profile_set: str, check_cringe: bool = False, cringe_threshold: float = 0.7):
        self.profile_set = profile_set
        self.profiles_dir = Path(f"profiles/{profile_set}")
        self.agents: dict[str, tuple[Agent, threading.Thread]] = {}
        self.check_cringe = check_cringe
        self.cringe_threshold = cringe_threshold

        with open(self.profiles_dir / "profile_generation_metadata.yaml") as f:
            self.metadata = yaml.safe_load(f)

    def load_agents(self) -> list[Agent]:
        """Load all agent personalities from the profiles directory."""
        agents = []
        for yaml_file in self.profiles_dir.glob("*.yaml"):
            if yaml_file.name != "profile_generation_metadata.yaml":
                agents.append(Agent(yaml_file, check_cringe=self.check_cringe, cringe_threshold=self.cringe_threshold))
        return agents

    def run_agent(self, agent: Agent):
        """Run a single agent in a loop."""
        try:
            logger.info("Starting agent: %s", agent.agent_name)
            agent.run_agent()
        except Exception as e:
            logger.error("Error running agent %s: %s", agent.agent_name, e)

    def start(self):
        """Start all agents in separate threads."""
        logger.info("Starting profile set %s with %d agents", self.profile_set, self.metadata["num_agents"])

        for agent in self.load_agents():
            thread = threading.Thread(
                target=self.run_agent, args=(agent,), name=f"Agent-{agent.agent_name}", daemon=True
            )
            self.agents[agent.agent_name] = (agent, thread)
            thread.start()

    def stop(self):
        """Stop all running agents."""
        logger.info("Stopping profile set %s", self.profile_set)
        # Note: Since threads are daemon=True, they'll be terminated when the main thread exits
        self.agents.clear()
