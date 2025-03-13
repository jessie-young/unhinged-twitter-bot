import json
import logging
from collections.abc import Generator
from typing import Any

import redis

from unhinged_twitter_bot.config import REDIS_EVENTS_PUBSUB_ADDR, REDIS_TWEET_TOPIC

logger = logging.getLogger(__name__)


class TwitterAPI:
    @classmethod
    def get_api(cls) -> "TwitterAPI":
        return TwitterAPI()

    def __init__(self):
        self.redis = redis.Redis.from_url(f"redis://{REDIS_EVENTS_PUBSUB_ADDR}")

    def make_tweet(self, content: str, author: str):
        tweet_data = {"author": author, "content": content}
        result = self.redis.publish(REDIS_TWEET_TOPIC, json.dumps(tweet_data))
        logger.info(
            "Published tweet to Redis pubsub `{}` with number of channels/subscribers alerted: {}",
            REDIS_TWEET_TOPIC,
            result,
        )

    def get_tweets(self, timeout: float | None = None) -> Generator[str, Any, Any]:
        r = redis.Redis.from_url(f"redis://{REDIS_EVENTS_PUBSUB_ADDR}")
        pubsub = r.pubsub()

        pubsub.subscribe(REDIS_TWEET_TOPIC)

        try:
            while True:
                message = pubsub.get_message(timeout=timeout)
                if message is None:
                    return
                if message["type"] == "message":
                    yield message["data"].decode("utf-8")
        finally:
            pubsub.unsubscribe()
