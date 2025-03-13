#!/usr/bin/env python3
"""
Twitter Data Collector

This script fetches tweets from the Twitter API based on defined topics,
processes them, and saves them to a file for further processing.
"""

import argparse
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twitter API credentials - from environment variables or .env file
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Define default topics to search for
DEFAULT_TOPICS = [
    "startup OR founder OR entrepreneur OR \"Y Combinator\" OR VC",
]

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
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
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
            },
            "topic_results": {}
        }
        
        for i, topic in enumerate(topics):
            print(f"Collecting tweets for topic: {topic}")
            result = self.search_tweets(topic, max_results=max_results)
            all_data["topic_results"][topic] = result
            
            # Respect rate limits, but only wait between topics, not after the last one
            if i < len(topics) - 1:
                wait_time = 15  # More conservative wait time between topics
                print(f"Waiting {wait_time} seconds before next request...")
                time.sleep(wait_time)
        
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
            filename = f"twitter_data_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {sum(len(topic_data['tweets']) for topic_data in data['topic_results'].values())} tweets to {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description="Collect Twitter data for specified topics")
    parser.add_argument("--topics", nargs="+", help="Topics to search for (space-separated)")
    parser.add_argument("--max-results", type=int, default=100, 
                        help="Maximum results per topic (10-100)")
    parser.add_argument("--output-dir", type=str, default="data/datasets",
                        help="Directory to save output files")
    parser.add_argument("--output-file", type=str, help="Output filename (optional)")
    
    args = parser.parse_args()
    
    # Check for Twitter API token
    if not BEARER_TOKEN:
        print("Error: TWITTER_BEARER_TOKEN environment variable not set")
        print("Please set it in your .env file or environment variables")
        return
    
    # Use default topics if none provided
    topics = args.topics if args.topics else DEFAULT_TOPICS
    
    # Initialize the collector
    collector = TwitterDataCollector(BEARER_TOKEN, args.output_dir)
    
    # Collect and save data
    data = collector.collect_from_topics(topics, max_results=args.max_results)
    collector.save_to_file(data, args.output_file)
    
    # Print summary
    total_tweets = sum(len(topic_data['tweets']) for topic_data in data['topic_results'].values())
    print(f"Collection complete! Fetched {total_tweets} tweets across {len(topics)} topics.")


if __name__ == "__main__":
    main() 