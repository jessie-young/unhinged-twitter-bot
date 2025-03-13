#!/usr/bin/env python3
"""
Twitter Data Collector

This script fetches tweets from the Twitter API based on defined topics or from specific authors,
processes them, and saves them to a file for further processing.

It supports two modes:
1. Topic mode: Collects tweets matching specific search queries/topics
2. Author mode: Collects tweets from specific Twitter accounts/authors
"""

import argparse
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twitter API credentials - from environment variables or .env file
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Define default topics to search for
DEFAULT_TOPICS = [
    "pmf OR a16z OR \"y combinator\" OR \"product market fit\"",
]

# Define default authors to collect tweets from
DEFAULT_AUTHORS = [
    # "paulg",       # Paul Graham
    # "sama",        # Sam Altman
    "naval",       # Naval Ravikant
    "jason",       # Jason Calacanis
    # "eladgil",     # Elad Gil
    # "garrytan",    # Garry Tan
    # "ycombinator", # Y Combinator
    # "techcrunch",  # TechCrunch
    # "a16z",        # Andreessen Horowitz
    # "sequoia",     # Sequoia Capital
]

# Twitter API rate limits
# For v2 API search_recent_tweets:
# - 450 requests per 15-minute window for Essential (free) access
# - 300 requests per 15-minute window for user_timeline
# We'll be conservative and assume 100 requests per window
RATE_LIMIT_WINDOW = 15 * 60  # 15 minutes in seconds
MAX_REQUESTS_PER_WINDOW = 100
REQUEST_INTERVAL = RATE_LIMIT_WINDOW / MAX_REQUESTS_PER_WINDOW  # Time between requests

class TwitterDataCollector:
    """Class to handle Twitter data collection and processing."""
    
    def __init__(self, bearer_token: str, output_dir: str = "data/datasets"):
        """
        Initialize the Twitter data collector.
        
        Args:
            bearer_token: Twitter API bearer token
            output_dir: Directory to save the collected data
        """
        self.client = tweepy.Client(bearer_token=bearer_token)
        self.output_dir = output_dir
        self.last_request_time = 0  # Track time of last request to manage rate limits
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def _wait_for_rate_limit(self):
        """
        Wait if needed to respect rate limits.
        Makes sure we don't exceed Twitter API rate limits.
        """
        now = time.time()
        time_since_last_request = now - self.last_request_time
        
        if time_since_last_request < REQUEST_INTERVAL:
            wait_time = REQUEST_INTERVAL - time_since_last_request
            print(f"Rate limit management: Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
            
        self.last_request_time = time.time()
    
    def search_tweets(
        self, 
        query: str, 
        max_results: int = 100, 
        tweet_fields: List[str] = None,
        user_fields: List[str] = None,
        expansions: List[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Search for tweets matching the given query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (10-100)
            tweet_fields: Fields to include in tweet objects
            user_fields: Fields to include in user objects
            expansions: Additional data to include with tweets
            max_retries: Maximum number of retry attempts for rate limits
            
        Returns:
            Dict containing tweets and associated data
        """
        # Wait for rate limit if needed
        self._wait_for_rate_limit()
        
        if tweet_fields is None:
            tweet_fields = [
                "id", "text", "author_id", "created_at", "public_metrics", 
                "referenced_tweets", "in_reply_to_user_id", "lang"
            ]
            
        if user_fields is None:
            user_fields = ["id", "name", "username", "description", "public_metrics"]
            
        if expansions is None:
            expansions = ["author_id", "referenced_tweets.id", "referenced_tweets.id.author_id"]
            
        # Add filters to query to exclude retweets and get English tweets
        full_query = f"{query} -is:retweet lang:en"
        
        # Search for tweets with retry logic
        retry_count = 0
        retry_delay = 5  # Start with 5 seconds delay
        
        while retry_count <= max_retries:
            try:
                response = self.client.search_recent_tweets(
                    query=full_query,
                    tweet_fields=tweet_fields,
                    user_fields=user_fields,
                    expansions=expansions,
                    max_results=max_results
                )
                
                # Process response
                result = {
                    "tweets": [],
                    "users": {},
                    "referenced_tweets": {},
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "count": 0 if response.data is None else len(response.data)
                }
                
                # Process users if included
                if response.includes and "users" in response.includes:
                    for user in response.includes["users"]:
                        result["users"][user.id] = user.data
                
                # Process referenced tweets if included
                if response.includes and "tweets" in response.includes:
                    for tweet in response.includes["tweets"]:
                        result["referenced_tweets"][tweet.id] = tweet.data
                
                # Process tweets
                if response.data:
                    for tweet in response.data:
                        # Convert to dict and add to result
                        tweet_dict = tweet.data
                        # Extra check for retweets (safety)
                        if not tweet.text.startswith("RT @"):
                            result["tweets"].append(tweet_dict)
                
                return result
                
            except tweepy.TweepyException as e:
                error_message = str(e)
                print(f"Error searching for tweets: {error_message}")
                
                # Handle rate limiting errors
                if "429" in error_message and retry_count < max_retries:
                    retry_count += 1
                    print(f"Rate limit exceeded. Retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})...")
                    time.sleep(retry_delay)
                    # Exponential backoff - double the delay for the next attempt
                    retry_delay *= 2
                else:
                    # Other errors or we've reached max retries
                    return {
                        "tweets": [], 
                        "users": {}, 
                        "referenced_tweets": {}, 
                        "query": query, 
                        "error": error_message, 
                        "count": 0
                    }
    
    def get_user_tweets(
        self,
        username: str,
        max_results: int = 100,
        tweet_fields: List[str] = None,
        user_fields: List[str] = None,
        expansions: List[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Get tweets from a specific user by username.
        
        Args:
            username: Twitter username (without the @ symbol)
            max_results: Maximum number of results to return (10-100)
            tweet_fields: Fields to include in tweet objects
            user_fields: Fields to include in user objects
            expansions: Additional data to include with tweets
            max_retries: Maximum number of retry attempts for rate limits
            
        Returns:
            Dict containing tweets and associated data
        """
        # Wait for rate limit if needed
        self._wait_for_rate_limit()
        
        if tweet_fields is None:
            tweet_fields = [
                "id", "text", "author_id", "created_at", "public_metrics", 
                "referenced_tweets", "in_reply_to_user_id", "lang"
            ]
            
        if user_fields is None:
            user_fields = ["id", "name", "username", "description", "public_metrics"]
            
        if expansions is None:
            expansions = ["author_id", "referenced_tweets.id", "referenced_tweets.id.author_id"]
        
        # First, get the user ID from the username
        try:
            user_response = self.client.get_user(username=username)
            if not user_response.data:
                print(f"User @{username} not found")
                return {
                    "tweets": [],
                    "users": {},
                    "referenced_tweets": {},
                    "username": username,
                    "error": f"User @{username} not found",
                    "count": 0
                }
            
            user_id = user_response.data.id
        except tweepy.TweepyException as e:
            error_message = str(e)
            print(f"Error getting user @{username}: {error_message}")
            return {
                "tweets": [],
                "users": {},
                "referenced_tweets": {},
                "username": username,
                "error": error_message,
                "count": 0
            }
        
        # Get the user's tweets
        retry_count = 0
        retry_delay = 5
        
        while retry_count <= max_retries:
            try:
                # Get user tweets - exclude retweets and replies for cleaner data
                response = self.client.get_users_tweets(
                    id=user_id,
                    exclude=["retweets", "replies"],
                    tweet_fields=tweet_fields,
                    user_fields=user_fields,
                    expansions=expansions,
                    max_results=max_results
                )
                
                # Process response
                result = {
                    "tweets": [],
                    "users": {},
                    "referenced_tweets": {},
                    "username": username,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "count": 0 if response.data is None else len(response.data)
                }
                
                # Process users if included
                if response.includes and "users" in response.includes:
                    for user in response.includes["users"]:
                        result["users"][user.id] = user.data
                
                # Process referenced tweets if included
                if response.includes and "tweets" in response.includes:
                    for tweet in response.includes["tweets"]:
                        result["referenced_tweets"][tweet.id] = tweet.data
                
                # Process tweets
                if response.data:
                    for tweet in response.data:
                        # Convert to dict and add to result
                        tweet_dict = tweet.data
                        result["tweets"].append(tweet_dict)
                
                return result
                
            except tweepy.TweepyException as e:
                error_message = str(e)
                print(f"Error getting tweets for @{username}: {error_message}")
                
                # Handle rate limiting errors
                if "429" in error_message and retry_count < max_retries:
                    retry_count += 1
                    print(f"Rate limit exceeded. Retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})...")
                    time.sleep(retry_delay)
                    # Exponential backoff
                    retry_delay *= 2
                else:
                    # Other errors or we've reached max retries
                    return {
                        "tweets": [],
                        "users": {},
                        "referenced_tweets": {},
                        "username": username,
                        "user_id": user_id if 'user_id' in locals() else None,
                        "error": error_message,
                        "count": 0
                    }
    
    def collect_from_topics(self, topics: List[str], max_results: int = 100) -> Dict[str, Any]:
        """
        Collect tweets for multiple topics.
        
        Args:
            topics: List of topic queries to search for
            max_results: Maximum results per topic
            
        Returns:
            Dict with all collected data
        """
        all_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "topics": topics,
                "collection_type": "topics"
            },
            "topic_results": {}
        }
        
        for i, topic in enumerate(topics):
            print(f"Collecting tweets for topic: {topic}")
            result = self.search_tweets(topic, max_results=max_results)
            all_data["topic_results"][topic] = result
            
            # Respect rate limits handled by _wait_for_rate_limit, but add a small buffer
            if i < len(topics) - 1:
                time.sleep(1)  # Small additional buffer between topics
        
        return all_data
    
    def collect_from_authors(self, authors: List[str], max_results: int = 100) -> Dict[str, Any]:
        """
        Collect tweets from multiple authors.
        
        Args:
            authors: List of Twitter usernames to collect from
            max_results: Maximum results per author
            
        Returns:
            Dict with all collected data
        """
        all_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "authors": authors,
                "collection_type": "authors"
            },
            "author_results": {}
        }
        
        for i, author in enumerate(authors):
            print(f"Collecting tweets from author: @{author}")
            result = self.get_user_tweets(author, max_results=max_results)
            all_data["author_results"][author] = result
            
            # Respect rate limits handled by _wait_for_rate_limit, but add a small buffer
            if i < len(authors) - 1:
                time.sleep(1)  # Small additional buffer between authors
        
        return all_data
    
    def save_to_file(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save collected data to a JSON file.
        
        Args:
            data: Collected tweet data
            filename: Optional filename, defaults to timestamp-based name
            
        Returns:
            Path to the saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            collection_type = data.get("metadata", {}).get("collection_type", "twitter")
            filename = f"{collection_type}_data_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Count tweets based on collection type
        total_tweets = 0
        if "topic_results" in data:
            total_tweets = sum(len(topic_data['tweets']) for topic_data in data['topic_results'].values())
        elif "author_results" in data:
            total_tweets = sum(len(author_data['tweets']) for author_data in data['author_results'].values())
            
        print(f"Saved {total_tweets} tweets to {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description="Collect Twitter data from topics or authors")
    parser.add_argument("--mode", type=str, choices=["topics", "authors"], default="topics",
                        help="Collection mode: 'topics' or 'authors' (default: topics)")
    parser.add_argument("--topics", nargs="+", help="Topics to search for (space-separated)")
    parser.add_argument("--authors", nargs="+", help="Twitter usernames to collect from (space-separated)")
    parser.add_argument("--max-results", type=int, default=100, 
                        help="Maximum results per topic/author (10-100)")
    parser.add_argument("--output-dir", type=str, default="data/datasets",
                        help="Directory to save output files")
    parser.add_argument("--output-file", type=str, help="Output filename (optional)")
    parser.add_argument("--max-requests", type=int, default=50,
                        help="Maximum number of API requests to make (default: 50)")
    
    args = parser.parse_args()
    
    # Check for Twitter API token
    if not BEARER_TOKEN:
        print("Error: TWITTER_BEARER_TOKEN environment variable not set")
        print("Please set it in your .env file or environment variables")
        return
    
    # Initialize the collector
    collector = TwitterDataCollector(BEARER_TOKEN, args.output_dir)
    
    # Determine mode and collection
    mode = args.mode
    
    if mode == "topics":
        # Use default topics if none provided
        topics = args.topics if args.topics else DEFAULT_TOPICS
        
        # Collect and save data
        print(f"Using topic mode with {len(topics)} topics")
        data = collector.collect_from_topics(topics, max_results=args.max_results)
        collector.save_to_file(data, args.output_file)
        
        # Print summary
        total_tweets = sum(len(topic_data['tweets']) for topic_data in data['topic_results'].values())
        print(f"Collection complete! Fetched {total_tweets} tweets across {len(topics)} topics.")
        
    elif mode == "authors":
        # Use default authors if none provided
        authors = args.authors if args.authors else DEFAULT_AUTHORS
        
        # Limit number of authors to avoid excessive API calls
        max_authors = min(len(authors), args.max_requests // 2)  # Each author requires at least 2 API calls
        if max_authors < len(authors):
            print(f"Warning: Limiting to {max_authors} authors to avoid exceeding rate limits")
            authors = authors[:max_authors]
        
        # Collect and save data
        print(f"Using author mode with {len(authors)} authors")
        data = collector.collect_from_authors(authors, max_results=args.max_results)
        collector.save_to_file(data, args.output_file)
        
        # Print summary
        total_tweets = sum(len(author_data['tweets']) for author_data in data['author_results'].values())
        print(f"Collection complete! Fetched {total_tweets} tweets from {len(authors)} authors.")


if __name__ == "__main__":
    main() 