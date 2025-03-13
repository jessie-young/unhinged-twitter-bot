import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .agent import run_agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_dir = Path(f"sessions/{session_id}")
        self.agents: dict[str, threading.Thread] = {}

        with open(self.session_dir / "session_metadata.yaml") as f:
            self.metadata = yaml.safe_load(f)

    def load_personalities(self) -> list[dict]:
        personalities = []
        for yaml_file in self.session_dir.glob("*.yaml"):
            if yaml_file.name != "session_metadata.yaml":
                with open(yaml_file) as f:
                    personalities.append(yaml.safe_load(f))
        return personalities

    def run_agent_with_personality(self, personality_path: Path):
        try:
            with open(personality_path) as f:
                personality = yaml.safe_load(f)

            agent_name = personality["name"]
            logger.info("Starting agent: %s", agent_name)

            thread = threading.Thread(
                target=run_agent,
                args=(personality_path,),
                name=f"Agent-{agent_name}",
                daemon=True,
            )
            self.agents[agent_name] = thread
            thread.start()

        except Exception as e:
            logger.error("Error starting agent with personality %s: %s", personality_path, e)

    def start(self):
        logger.info("Starting session %s with %d agents", self.session_id, self.metadata["num_agents"])

        with ThreadPoolExecutor(max_workers=min(32, self.metadata["num_agents"])) as executor:
            personality_files = list(self.session_dir.glob("*.yaml"))
            personality_files = [f for f in personality_files if f.name != "session_metadata.yaml"]
            executor.map(self.run_agent_with_personality, personality_files)

    def stop(self):
        logger.info("Stopping session %s", self.session_id)
