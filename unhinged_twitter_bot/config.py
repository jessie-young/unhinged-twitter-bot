from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.dev")

import os

REDIS_TWEET_TOPIC = os.environ["REDIS_TWEET_TOPIC"]
REDIS_EVENTS_PUBSUB_ADDR = os.environ["REDIS_EVENTS_PUBSUB_ADDR"]
AGENT_LOG_FOLDER = os.environ["AGENT_LOG_FOLDER"]
