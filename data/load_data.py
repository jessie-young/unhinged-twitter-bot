import lancedb
import json
import argparse
import time
import uuid
import logging
# import pandas as pd
# import pyarrow as pa
import daft
import pandas as pd
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize embedding function
embedding_func = get_registry().get("sentence-transformers").create(
    name="BAAI/bge-small-en-v1.5", 
    device="cpu"
)

# Define LanceDB model with additional columns - same as tweet_embedding_service.py
class Tweet(LanceModel):
    text: str = embedding_func.SourceField()
    vector: Vector(embedding_func.ndims()) = embedding_func.VectorField()
    tweet_id: str = None
    username: str = None
    author_id: str = None
    retweets: int = 0
    likes: int = 0
    created_at: float = None
    reply_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    impression_count: int = 0
    lang: str = None

def load_tweets_from_json(json_file):
    """Load tweets from a JSON file"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded data from {json_file}")
            
            if not isinstance(data, dict):
                raise ValueError(f"Expected JSON to be a dictionary, but got {type(data)}")
                
            logger.info(f"JSON data has keys: {list(data.keys())}")
            
            # Check if we have the expected structure
            if 'topic_results' not in data:
                raise ValueError("Missing 'topic_results' in JSON data")
                
            topic_results = data['topic_results']
            
            # Find the first topic key (or use the topic name if specified in metadata)
            topic_key = None
            if 'metadata' in data and 'topics' in data['metadata'] and data['metadata']['topics']:
                topic_key = data['metadata']['topics'][0]
                
            if not topic_key and topic_results:
                # Take the first key in topic_results
                topic_key = next(iter(topic_results.keys()))
                
            if not topic_key or topic_key not in topic_results:
                raise ValueError(f"Could not find valid topic key in topic_results, available keys: {list(topic_results.keys())}")
                
            # Extract tweets from the topic_results
            topic_data = topic_results[topic_key]
            
            if not isinstance(topic_data, dict) or 'tweets' not in topic_data:
                raise ValueError(f"Topic data should contain 'tweets' field, but got: {list(topic_data.keys()) if isinstance(topic_data, dict) else type(topic_data)}")
                
            tweets = topic_data['tweets']
            
            if not isinstance(tweets, list):
                raise ValueError(f"Expected tweets to be a list, but got {type(tweets)}")
                
            logger.info(f"Found {len(tweets)} tweets in topic '{topic_key}'")
            return tweets
                
    except json.JSONDecodeError as e:
        # Print more context around the error
        with open(json_file, 'r') as f:
            lines = f.readlines()
            
        line_no = e.lineno - 1  # adjust for 0-based indexing
        context_lines = 5
        start_line = max(0, line_no - context_lines)
        end_line = min(len(lines), line_no + context_lines + 1)
        
        logger.error(f"JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}")
        logger.error("Context:")
        for i in range(start_line, end_line):
            prefix = ">" if i == line_no else " "
            logger.error(f"{prefix} Line {i+1}: {lines[i].strip()}")
            
        raise ValueError(f"Failed to parse JSON file {json_file}: {e}")
    except Exception as e:
        logger.error(f"Error loading tweets from {json_file}: {e}")
        raise

def process_tweet(tweet):
    """Process a tweet and prepare it for LanceDB"""
    try:
        # Ensure tweet is a dictionary
        if not isinstance(tweet, dict):
            logger.error(f"Expected tweet to be a dictionary, but got {type(tweet)}")
            return None
            
        # Get the tweet text
        if 'text' not in tweet:
            logger.warning(f"Tweet missing 'text' field: {tweet}")
            return None
            
        tweet_text = tweet['text']
        
        # Extract fields with proper fallbacks
        tweet_id = tweet.get('id', str(uuid.uuid4()))
        author_id = tweet.get('author_id', 'unknown')
        username = tweet.get('username', author_id)  # Use author_id as fallback for username
        lang = tweet.get('lang', 'en')
        
        # Extract created_at timestamp
        created_at = time.time()  # Default to current time
        if 'created_at' in tweet:
            created_at_str = tweet['created_at']
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')).timestamp()
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse created_at '{created_at_str}': {e}")
        
        # Extract metrics from public_metrics if available
        public_metrics = tweet.get('public_metrics', {})
        retweets = int(public_metrics.get('retweet_count', 0))
        likes = int(public_metrics.get('like_count', 0))
        reply_count = int(public_metrics.get('reply_count', 0))
        quote_count = int(public_metrics.get('quote_count', 0))
        bookmark_count = int(public_metrics.get('bookmark_count', 0))
        impression_count = int(public_metrics.get('impression_count', 0))
        
        # Create tweet record with all fields
        return {
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
    except Exception as e:
        import traceback
        logger.error(f"Error processing tweet {tweet.get('id', 'unknown')}: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Load tweets into LanceDB')
    parser.add_argument('--input-json', required=True, help='Path to the JSON file containing tweets')
    parser.add_argument('--db-uri', default='./data/lancedb', help='Path to the LanceDB database directory (default: ./data/lancedb)')
    parser.add_argument('--table-name', default='tweets', help='Name of the table to create (default: tweets)')
    args = parser.parse_args()
    
    try:
        # LanceDB setup
        uri = args.db_uri
        logger.info(f"Connecting to LanceDB at {uri}")
        db = lancedb.connect(uri)

        # Load tweets from JSON file
        try:
            tweets = load_tweets_from_json(args.input_json)
            logger.info(f"Successfully loaded {len(tweets)} tweets from {args.input_json}")
        except Exception as e:
            logger.error(f"Failed to load tweets from {args.input_json}: {e}")
            return 1  # Exit with error code
        
        if not tweets:
            logger.error("No tweets found in the JSON file")
            return 1
        
        # Process tweets
        processed_tweets = []
        for i, tweet in enumerate(tweets):
            try:
                processed_tweet = process_tweet(tweet)
                if processed_tweet:
                    processed_tweets.append(processed_tweet)
            except Exception as e:
                logger.error(f"Error processing tweet #{i}: {e}")
        
        if not processed_tweets:
            logger.error("No tweets could be processed successfully")
            return 1
            
        logger.info(f"Processed {len(processed_tweets)} tweets successfully")
        
        # Create a LanceDB table with the embeddings and other metadata
        table_name = args.table_name
        logger.info(f"Creating table '{table_name}' with {len(processed_tweets)} tweets")
        
        # Create the table and add the data
        table = db.create_table(table_name, schema=Tweet, mode="overwrite")
        
        try:
            table.add(processed_tweets)
            logger.info(f"Added {len(processed_tweets)} tweets to table '{table_name}'")
            
            # Create an index for faster retrieval
            # Commented out since this was causing issues
            # logger.info(f"Creating index for table '{table_name}'")
            # try:
            #     table.create_index()
            #     logger.info(f"Created index for table '{table_name}'")
            # except Exception as e:
            #     logger.warning(f"Error creating index: {e}")
            #     logger.warning("Continuing without index creation")
                
            # Dump the table contents
            logger.info(f"Dumping contents of table '{table_name}':")
            try:
                records = table.to_pandas()
                if len(records) > 0:
                    # Remove the vector column to make output cleaner
                    if 'vector' in records.columns:
                        records = records.drop(columns=['vector'])
                    
                    # Print summary of the table
                    logger.info(f"Table contains {len(records)} records")
                    logger.info(f"Columns: {list(records.columns)}")
                    
                    # Display the first few records (max 5)
                    display_count = min(5, len(records))
                    for i in range(display_count):
                        record = records.iloc[i]
                        logger.info(f"Record #{i+1}:")
                        for col in records.columns:
                            value = record[col]
                            # Truncate long text fields
                            if col == 'text' and isinstance(value, str) and len(value) > 100:
                                value = value[:100] + '...'
                            logger.info(f"  {col}: {value}")
                    
                    if len(records) > display_count:
                        logger.info(f"... and {len(records) - display_count} more records")
                else:
                    logger.info("Table is empty")
            except Exception as e:
                logger.error(f"Error dumping table contents: {e}")
                
        except Exception as e:
            logger.error(f"Error adding tweets to table: {e}")
            logger.error("Please check that your data matches the schema")
            return 1
        
        logger.info(f"Completed loading tweets into table '{table_name}' at {uri}")
        return 0  # Success
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    import sys
    sys.exit(exit_code)
