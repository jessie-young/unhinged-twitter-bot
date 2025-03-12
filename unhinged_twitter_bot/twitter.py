import redis
import logging

from unhinged_twitter_bot.config import REDIS_EVENTS_PUBSUB_ADDR, REDIS_TWEET_TOPIC

from typing import Any, Generator

logger = logging.getLogger(__name__)

class TwitterAPI:

    @classmethod
    def get_api(cls) -> "TwitterAPI":
        return TwitterAPI()
    
    def __init__(self):
        self.redis = r = redis.Redis.from_url(f"redis://{REDIS_EVENTS_PUBSUB_ADDR}")

    def make_tweet(self, content: str, author: str):
        tweet_data = {
            "author": author,
            "content": content
        }
        # TODO: we should also make an actual tweet to Twitter using an API key
        result = self.redis.publish(REDIS_TWEET_TOPIC, str(tweet_data))
        logger.info("Published tweet to Redis pubsub `{}` with number of channels/subscribers alerted: {}", REDIS_TWEET_TOPIC, result)

    def get_tweets(self) -> Generator[str, Any, Any]:
        r = redis.Redis.from_url(f"redis://{REDIS_EVENTS_PUBSUB_ADDR}")
        pubsub = r.pubsub()

        logger.info("Subscribing to Redis pubsub `{}`", REDIS_TWEET_TOPIC)
        pubsub.subscribe(REDIS_TWEET_TOPIC)

        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    yield message['data'].decode('utf-8')
        finally:
            pubsub.unsubscribe()
