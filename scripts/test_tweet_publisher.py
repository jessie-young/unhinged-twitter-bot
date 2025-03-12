#!/usr/bin/env python3
import redis
import json
import argparse
import uuid
import time
import random

def publish_test_tweet(host='localhost', port=6379, text=None, username=None):
    """
    Publish a test tweet to the Redis 'tweets' channel
    """
    # Connect to Redis
    r = redis.Redis(host=host, port=port)
    
    # Create tweet data
    if text is None:
        text = "This is a test tweet published at " + str(uuid.uuid4()) + " #testing #embedding"
    
    if username is None:
        username = f"user_{random.randint(1000, 9999)}"
    
    tweet_data = {
        "id": str(uuid.uuid4()),
        "text": text,
        "username": username,
        "retweets": random.randint(0, 1000),
        "likes": random.randint(0, 5000),
        "timestamp": time.time()
    }
    
    # Convert to JSON
    tweet_json = json.dumps(tweet_data)
    
    # Publish to channel
    result = r.publish('tweets', tweet_json)
    
    print(f"Published tweet from {tweet_data['username']}: {tweet_data['text']}")
    print(f"Retweets: {tweet_data['retweets']}, Likes: {tweet_data['likes']}")
    print(f"Number of receivers: {result}")
    
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Publish a test tweet to Redis')
    parser.add_argument('--host', type=str, default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--text', type=str, help='Custom tweet text (optional)')
    parser.add_argument('--username', type=str, help='Username (optional)')
    
    args = parser.parse_args()
    
    publish_test_tweet(host=args.host, port=args.port, text=args.text, username=args.username) 