#!/usr/bin/env python3
import os
import json
import time
import redis
import lancedb
import uuid
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection
REDIS_HOST = os.environ.get('REDIS_EVENTS_PUBSUB_ADDR', 'localhost:6379')
host, port = REDIS_HOST.split(':')
redis_client = redis.Redis(host=host, port=int(port))

# LanceDB setup
uri = "/app/data/lancedb"
db = lancedb.connect(uri)

# Initialize embedding function
embedding_func = get_registry().get("sentence-transformers").create(
    name="BAAI/bge-small-en-v1.5", 
    device="cpu"
)

# Define LanceDB model with additional columns
class Tweet(LanceModel):
    text: str = embedding_func.SourceField()
    vector: Vector(embedding_func.ndims()) = embedding_func.VectorField()
    tweet_id: str = None
    username: str = None
    retweets: int = 0
    likes: int = 0
    timestamp: float = None

# Create or open table
if "tweets" in db.table_names():
    table = db.open_table("tweets")
    logger.info("Opened existing 'tweets' table")
else:
    table = db.create_table("tweets", schema=Tweet)
    logger.info("Created new 'tweets' table")

# Subscribe to the tweet channel
pubsub = redis_client.pubsub()
pubsub.subscribe('tweets')
logger.info("Subscribed to 'tweets' channel")

def process_tweet(tweet_data):
    """Process a tweet and add its embedding to LanceDB"""
    try:
        # Parse tweet data
        tweet = json.loads(tweet_data)
        
        # Check if this is the TwitterAPI format (with author/content) or the expected format (with text/id)
        if 'content' in tweet and 'author' in tweet:
            # This is from TwitterAPI
            tweet_text = tweet.get('content', '')
            username = tweet.get('author', '')
            tweet_id = str(uuid.uuid4())  # Generate a UUID since there's no ID
            retweets = 0
            likes = 0
            timestamp = time.time()
            logger.info(f"Received tweet in TwitterAPI format from {username}")
        else:
            # This is the expected format
            tweet_text = tweet.get('text', '')
            username = tweet.get('username', '')
            tweet_id = tweet.get('id', str(uuid.uuid4()))
            retweets = int(tweet.get('retweets', 0))
            likes = int(tweet.get('likes', 0))
            timestamp = tweet.get('timestamp', time.time())
        
        if not tweet_text:
            logger.warning(f"Received empty tweet text for tweet ID {tweet_id}")
            return
            
        # Create tweet record with embedding and all the additional fields
        tweet_record = {
            "text": tweet_text,
            "tweet_id": tweet_id,
            "username": username,
            "retweets": retweets,
            "likes": likes,
            "timestamp": timestamp
        }
        
        # Add to LanceDB
        table.add([tweet_record])
        logger.info(f"Added tweet {tweet_id} from {username} to LanceDB")
        
    except Exception as e:
        logger.error(f"Error processing tweet: {e}")

def main():
    logger.info("Tweet embedding service started")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                tweet_data = message['data']
                if isinstance(tweet_data, bytes):
                    tweet_data = tweet_data.decode('utf-8')
                    
                logger.info(f"Received new tweet")
                process_tweet(tweet_data)
                
    except KeyboardInterrupt:
        logger.info("Service shutting down")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        pubsub.unsubscribe()
        redis_client.close()

if __name__ == "__main__":
    main() 