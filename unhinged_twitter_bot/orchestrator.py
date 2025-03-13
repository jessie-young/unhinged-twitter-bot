import logging
import threading
from pathlib import Path

import yaml

from .agent import Agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_dir = Path(f"sessions/{session_id}")
        self.agents: dict[str, tuple[Agent, threading.Thread]] = {}

        with open(self.session_dir / "session_metadata.yaml") as f:
            self.metadata = yaml.safe_load(f)

    def load_agents(self) -> list[Agent]:
        """Load all agent personalities from the session directory."""
        agents = []
        for yaml_file in self.session_dir.glob("*.yaml"):
            if yaml_file.name != "session_metadata.yaml":
                agents.append(Agent(yaml_file))
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
        logger.info("Starting session %s with %d agents", self.session_id, self.metadata["num_agents"])

        for agent in self.load_agents():
            thread = threading.Thread(
                target=self.run_agent, args=(agent,), name=f"Agent-{agent.agent_name}", daemon=True
            )
            self.agents[agent.agent_name] = (agent, thread)
            thread.start()

    def stop(self):
        """Stop all running agents."""
        logger.info("Stopping session %s", self.session_id)
        # Note: Since threads are daemon=True, they'll be terminated when the main thread exits
        self.agents.clear()
