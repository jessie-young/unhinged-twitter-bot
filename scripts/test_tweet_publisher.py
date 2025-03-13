#!/usr/bin/env python3
import redis
import json
import argparse
import uuid
import time
import random

def publish_test_tweet(host='localhost', port=6379, text=None, username=None, author_id=None, lang=None):
    """
    Publish a test tweet to the Redis 'tweets' channel with fields matching the new LanceDB schema
    """
    # Connect to Redis
    r = redis.Redis(host=host, port=port)
    
    # Create tweet data
    if text is None:
        text = "This is a test tweet published at " + str(uuid.uuid4()) + " #testing #embedding"
    
    if username is None:
        username = f"user_{random.randint(1000, 9999)}"
    
    if author_id is None:
        author_id = username  # Default author_id to username if not provided
    
    if lang is None:
        lang = "en"  # Default language to English
    
    # Generate random metrics
    retweets = random.randint(0, 1000)
    likes = random.randint(0, 5000)
    reply_count = random.randint(0, 500)
    quote_count = random.randint(0, 200)
    bookmark_count = random.randint(0, 100)
    impression_count = random.randint(1000, 50000)
    
    # Create tweet data conforming to the new schema
    tweet_data = {
        "id": str(uuid.uuid4()),
        "text": text,
        "username": username,
        "author_id": author_id,
        "retweets": retweets,
        "likes": likes,
        "created_at": time.time(),  # Renamed from timestamp
        "reply_count": reply_count,
        "quote_count": quote_count,
        "bookmark_count": bookmark_count,
        "impression_count": impression_count,
        "lang": lang
    }
    
    # Convert to JSON
    tweet_json = json.dumps(tweet_data)
    
    # Publish to channel
    result = r.publish('tweets', tweet_json)
    
    print(f"Published tweet from {tweet_data['username']} (author_id: {tweet_data['author_id']})")
    print(f"Text: {tweet_data['text']}")
    print(f"Metrics: Retweets: {retweets}, Likes: {likes}, Replies: {reply_count}, Quotes: {quote_count}")
    print(f"Additional: Bookmarks: {bookmark_count}, Impressions: {impression_count}, Language: {lang}")
    print(f"Number of receivers: {result}")
    
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Publish a test tweet to Redis matching the new LanceDB schema')
    parser.add_argument('--host', type=str, default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--text', type=str, help='Custom tweet text (optional)')
    parser.add_argument('--username', type=str, help='Username (optional)')
    parser.add_argument('--author-id', type=str, help='Author ID (optional, defaults to username)')
    parser.add_argument('--lang', type=str, default='en', help='Language code (optional, defaults to "en")')
    
    args = parser.parse_args()
    
    publish_test_tweet(
        host=args.host, 
        port=args.port, 
        text=args.text, 
        username=args.username,
        author_id=args.author_id,
        lang=args.lang
    ) 