import contextlib
import json
import os
from collections.abc import Generator
from typing import Any

from unhinged_twitter_bot.config import AGENT_LOG_FOLDER


class AgentSessionLogger:
    def __init__(self, session_id: str, log_dump_folder: str):
        self.log_dump_folder = log_dump_folder
        self.session_id = session_id
        self.log_file = None

        self.session_log_idx = 0

    def __enter__(self):
        self.log_file = open(f"{self.log_dump_folder}/session_{self.session_id}.jsonl", "a")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.log_file:
            self.log_file.close()

    def log_prompt(self, prompt_type: str, prompt: str, response: str) -> None:
        if self.log_file:
            self.log_file.write(
                json.dumps(
                    {
                        "session_id": self.session_id,
                        "log_idx": self.session_log_idx,
                        "type": "prompt",
                        "prompt_type": prompt_type,
                        "data": {
                            "prompt": prompt,
                            "response": response,
                        },
                    }
                )
            )
            self.log_file.write("\n")
            self.log_file.flush()
        self.session_log_idx += 1

    def log_hdb_mcp_call(self, mcp_request: dict, mcp_response: dict) -> None:
        if self.log_file:
            self.log_file.write(
                json.dumps(
                    {
                        "session_id": self.session_id,
                        "log_idx": self.session_log_idx,
                        "type": "mcp_hdb",
                        "data": {
                            "request": mcp_request,
                            "response": mcp_response,
                        },
                    }
                )
            )
            self.log_file.write("\n")
            self.log_file.flush()
        self.session_log_idx += 1


class AgentLogger:
    def __init__(self, agent_name: str, log_dump_folder: str = AGENT_LOG_FOLDER):
        self.log_dump_folder = log_dump_folder
        os.makedirs(log_dump_folder, exist_ok=True)
        self.agent_name = agent_name

    @contextlib.contextmanager
    def session_logger(self, session_id: str) -> Generator[AgentSessionLogger, Any, Any]:
        with AgentSessionLogger(session_id, self.log_dump_folder) as logger:
            yield logger
