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
    author_id: str = None
    retweets: int = 0
    likes: int = 0
    created_at: float = None  # Renamed from timestamp
    reply_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    impression_count: int = 0
    lang: str = None

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
            author_id = tweet.get('author_id', username)
            retweets = 0
            likes = 0
            created_at = time.time()
            reply_count = 0
            quote_count = 0
            bookmark_count = 0
            impression_count = 0
            lang = tweet.get('lang', 'en')
            logger.info(f"Received tweet in TwitterAPI format from {username}")
        else:
            # This is the expected format
            tweet_text = tweet.get('text', '')
            username = tweet.get('username', '')
            tweet_id = tweet.get('id', str(uuid.uuid4()))
            author_id = tweet.get('author_id', username)
            
            # Extract metrics
            retweets = int(tweet.get('retweets', 0))
            likes = int(tweet.get('likes', 0))
            reply_count = int(tweet.get('reply_count', 0))
            quote_count = int(tweet.get('quote_count', 0))
            bookmark_count = int(tweet.get('bookmark_count', 0))
            impression_count = int(tweet.get('impression_count', 0))
            
            # Convert timestamp or use created_at directly
            if 'created_at' in tweet:
                created_at = tweet.get('created_at')
                # If created_at is a string, try to convert to timestamp
                if isinstance(created_at, str):
                    try:
                        from datetime import datetime
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                    except (ValueError, TypeError):
                        created_at = time.time()
            else:
                created_at = tweet.get('timestamp', time.time())
                
            lang = tweet.get('lang', 'en')
        
        if not tweet_text:
            logger.warning(f"Received empty tweet text for tweet ID {tweet_id}")
            return
            
        # Create tweet record with embedding and all the additional fields
        tweet_record = {
            "text": tweet_text,
            "tweet_id": tweet_id,
            "username": username,
            "author_id": author_id,
            "retweets": retweets,
            "likes": likes,
            "created_at": created_at,
            "reply_count": reply_count,
            "quote_count": quote_count,
            "bookmark_count": bookmark_count,
            "impression_count": impression_count,
            "lang": lang
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