#!/usr/bin/env python3
"""
Batch Tweet Publisher

This script reads tweets from a JSON dataset and publishes them to Redis
one by one, mimicking the format expected by the tweet embedding service.

Usage:
    With local Redis:
        python scripts/batch_publish_tweets.py data/datasets/twitter_data_20250312_164318.json
    
    With Docker Redis:
        python scripts/batch_publish_tweets.py data/datasets/twitter_data_20250312_164318.json --host events-pubsub
    
    If you're running with docker-compose, you can use 'events-pubsub' as the host to connect
    to the Redis container defined in docker-compose.yml.
    
    To limit the number of tweets:
        python scripts/batch_publish_tweets.py data/datasets/twitter_data_20250312_164318.json --max-tweets 10
"""

import argparse
import json
import os
import redis
import time
import uuid
from datetime import datetime
import logging
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def transform_tweet(tweet_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform tweet data from the dataset format to the expected Redis format.
    
    Args:
        tweet_data: Tweet data from the dataset
        
    Returns:
        Transformed tweet data in the format expected by the embedding service
    """
    # Extract relevant fields based on the dataset format
    # The function handles two possible formats:
    # 1. Twitter API format with nested structures
    # 2. Already formatted tweets with text, username, etc.
    
    if 'text' in tweet_data and 'username' in tweet_data and 'author_id' in tweet_data:
        # Data may already be in the expected format, but we'll still ensure all fields exist
        output = tweet_data.copy()
        
        # Make sure all required fields exist, setting defaults if not
        if 'created_at' not in output and 'timestamp' in output:
            output['created_at'] = output.pop('timestamp')
        
        # Ensure all metrics exist
        output.setdefault('reply_count', 0)
        output.setdefault('quote_count', 0)
        output.setdefault('bookmark_count', 0)
        output.setdefault('impression_count', 0)
        output.setdefault('lang', 'en')
        
        return output
    
    # Check if this is a Twitter API response with public_metrics
    if 'public_metrics' in tweet_data and 'text' in tweet_data:
        # This is individual tweet data from the Twitter API
        text = tweet_data.get('text', '')
        tweet_id = tweet_data.get('id', str(uuid.uuid4()))
        
        # Get username and author_id fields
        author_id = tweet_data.get('author_id', f"user_{str(uuid.uuid4())[:8]}")
        # Default username to author_id if not available
        username = tweet_data.get('username', author_id)
        
        # Extract metrics if available
        metrics = tweet_data.get('public_metrics', {})
        retweets = metrics.get('retweet_count', 0)
        likes = metrics.get('like_count', 0)
        reply_count = metrics.get('reply_count', 0)
        quote_count = metrics.get('quote_count', 0)
        bookmark_count = metrics.get('bookmark_count', 0)
        impression_count = metrics.get('impression_count', 0)
        
        # Get language if available
        lang = tweet_data.get('lang', 'en')
        
        # Convert created_at string to timestamp if available
        created_at = tweet_data.get('created_at')
        if created_at:
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
            except (ValueError, TypeError):
                created_at = time.time()
        else:
            created_at = time.time()
    else:
        # Default fallback for unknown format
        text = str(tweet_data)
        tweet_id = str(uuid.uuid4())
        author_id = f"user_{str(uuid.uuid4())[:8]}"
        username = author_id
        retweets = 0
        likes = 0
        reply_count = 0
        quote_count = 0
        bookmark_count = 0
        impression_count = 0
        lang = 'en'
        created_at = time.time()
    
    # Create the tweet in the expected format with all fields
    return {
        "id": tweet_id,
        "text": text,
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

def read_tweets_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read tweets from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of tweet data
    """
    logger.info(f"Reading tweets from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tweets = []
        
        # Special case for the twitter_data_* files with topic_results structure
        if isinstance(data, dict) and 'topic_results' in data:
            # This is the structure we found in twitter_data_20250312_164318.json
            for topic, topic_data in data['topic_results'].items():
                if 'tweets' in topic_data and isinstance(topic_data['tweets'], list):
                    logger.info(f"Found tweets for topic: {topic}")
                    tweets.extend(topic_data['tweets'])
                    
        # Check if this is a Twitter API response with 'data' field
        elif isinstance(data, dict):
            if 'data' in data and isinstance(data['data'], list):
                # Twitter API format with a list of tweets
                tweets.extend(data['data'])
            elif 'includes' in data and 'tweets' in data.get('includes', {}):
                # Twitter API format with included tweets
                tweets.extend(data['includes']['tweets'])
            elif 'tweets' in data:
                # JSON with 'tweets' field containing all tweets
                tweets_data = data['tweets']
                if isinstance(tweets_data, dict):
                    # If tweets are stored as a dictionary with IDs as keys
                    for tweet_id, tweet in tweets_data.items():
                        if isinstance(tweet, dict):
                            tweet['id'] = tweet.get('id', tweet_id)
                            tweets.append(tweet)
                elif isinstance(tweets_data, list):
                    # If tweets are stored as a list
                    tweets.extend(tweets_data)
        elif isinstance(data, list):
            # List of tweet objects
            tweets.extend(data)
        
        logger.info(f"Found {len(tweets)} tweets in the dataset")
        return tweets
    
    except Exception as e:
        logger.error(f"Error reading tweets from file: {e}")
        return []

def publish_tweets_to_redis(tweets: List[Dict[str, Any]], host: str = 'localhost', port: int = 6379, 
                          delay: float = 0.1, max_tweets: int = None, debug: bool = False) -> int:
    """
    Publish tweets to Redis.
    
    Args:
        tweets: List of tweet data
        host: Redis host
        port: Redis port
        delay: Delay between publishing tweets (in seconds)
        max_tweets: Maximum number of tweets to publish (None for all)
        debug: Whether to print debug information
        
    Returns:
        Number of tweets published
    """
    logger.info(f"Connecting to Redis at {host}:{port}")
    
    try:
        r = redis.Redis(host=host, port=port, socket_connect_timeout=5)
        
        # Check Redis connection
        try:
            r.ping()
            logger.info("Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.error("Make sure Redis is running at the specified host and port")
            logger.error("If using docker-compose, run 'docker-compose up events-pubsub' first")
            logger.error("Then use --host events-pubsub when running this script")
            return 0
        
        published_count = 0
        tweets_to_publish = tweets[:max_tweets] if max_tweets else tweets
        
        logger.info(f"Publishing {len(tweets_to_publish)} tweets to Redis channel 'tweets'")
        
        for i, tweet_data in enumerate(tweets_to_publish):
            try:
                # Transform tweet to expected format
                transformed_tweet = transform_tweet(tweet_data)
                
                # Show sample of first tweet for debugging
                if i == 0 or debug:
                    logger.info(f"Sample transformed tweet (showing first 3 fields):")
                    sample_fields = {k: transformed_tweet[k] for k in list(transformed_tweet.keys())[:3]}
                    logger.info(f"  {sample_fields}...")
                    logger.info(f"  Fields included: {list(transformed_tweet.keys())}")
                
                # Convert to JSON
                tweet_json = json.dumps(transformed_tweet)
                
                # Publish to channel
                result = r.publish('tweets', tweet_json)
                
                published_count += 1
                
                if i % 100 == 0 or i == len(tweets_to_publish) - 1:
                    logger.info(f"Published {i+1}/{len(tweets_to_publish)} tweets")
                
                # Add delay to avoid overwhelming Redis
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error publishing tweet {i}: {e}")
        
        logger.info(f"Successfully published {published_count} tweets")
        return published_count
    
    except Exception as e:
        logger.error(f"Unexpected error during Redis connection or publishing: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='Batch publish tweets from a dataset to Redis')
    parser.add_argument('file_path', type=str, help='Path to the JSON dataset file')
    parser.add_argument('--host', type=str, default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--delay', type=float, default=0.1, 
                        help='Delay between publishing tweets (in seconds)')
    parser.add_argument('--max-tweets', type=int, default=None, 
                        help='Maximum number of tweets to publish (default: all)')
    parser.add_argument('--debug', action='store_true',
                        help='Print debug information for each tweet')
    
    args = parser.parse_args()
    
    # Validate file path
    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        return
    
    # Read tweets from file
    tweets = read_tweets_from_file(args.file_path)
    
    if not tweets:
        logger.error("No tweets found in the dataset")
        return
    
    # Publish tweets to Redis
    publish_tweets_to_redis(
        tweets, 
        host=args.host, 
        port=args.port, 
        delay=args.delay, 
        max_tweets=args.max_tweets,
        debug=args.debug
    )

if __name__ == "__main__":
    main() 