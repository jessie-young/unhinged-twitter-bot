import uuid

from unhinged_twitter_bot.activity_logging import AgentLogger

if __name__ == "__main__":
    logging = AgentLogger("dumb_logging_agent")
    with logging.session_logger(str(uuid.uuid4())) as logger:
        for i in range(5):
            logger.log_prompt(f"Tell me a story {i}", f"hello world {i}")
