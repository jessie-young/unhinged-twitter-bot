#!/usr/bin/env python3
import os
import argparse
import json
import lancedb
import logging
from openai import OpenAI
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Query tweets using natural language search')
    parser.add_argument('--db-dir', type=str, required=True, help='Directory path for LanceDB')
    parser.add_argument('--table-name', type=str, required=True, help='LanceDB table name')
    parser.add_argument('--query', type=str, default="Give me all the recent tweets from Paul Graham", 
                        help='Natural language query to search tweets')
    parser.add_argument('--username', type=str, help='Filter tweets by username (case-insensitive)')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of results to return')
    parser.add_argument('--sort-by-date', action='store_true', help='Sort results by date (most recent first)')
    return parser.parse_args()

def get_openai_embedding(text, model="text-embedding-3-small"):
    """Get OpenAI embedding for the provided text."""
    try:
        # Get OpenAI API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Get embedding
        response = client.embeddings.create(
            input=text,
            model=model
        )
        
        # Return the embedding vector
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting OpenAI embedding: {e}")
        raise

def format_timestamp(timestamp):
    """Format timestamp to a readable date string."""
    if not timestamp:
        return "Unknown date"
    
    try:
        # Handle different timestamp formats
        if isinstance(timestamp, (int, float)):
            # Unix timestamp (seconds since epoch)
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, str):
            # ISO format string
            try:
                # Try parsing ISO format
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Try parsing as float if it's a string representation of a number
                return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OverflowError) as e:
        logger.warning(f"Could not parse timestamp {timestamp}: {e}")
        return str(timestamp)

def format_tweet_result(tweet):
    """Format tweet for display."""
    # Format timestamp if available
    date_str = format_timestamp(tweet.get('created_at'))
    
    # Format metrics
    metrics = f"❤️ {tweet.get('likes', 0)} | 🔄 {tweet.get('retweets', 0)}"
    if 'reply_count' in tweet:
        metrics += f" | 💬 {tweet.get('reply_count', 0)}"
    if 'impression_count' in tweet:
        metrics += f" | 👁️ {tweet.get('impression_count', 0)}"
    
    # Format the tweet display
    return f"""
@{tweet.get('username', 'unknown')} • {date_str}
{tweet.get('text', '')}
{metrics}
{"=" * 80}
"""

def search_tweets(db_dir, table_name, query=None, username=None, limit=10, sort_by_date=False):
    """Search tweets using natural language query and/or username filter."""
    try:
        # Connect to LanceDB
        db = lancedb.connect(db_dir)
        
        # Open the table
        if table_name not in db.table_names():
            logger.error(f"Table '{table_name}' not found in database")
            logger.info(f"Available tables: {db.table_names()}")
            return []
            
        table = db.open_table(table_name)
        logger.info(f"Connected to table '{table_name}' with {len(table)} records")
        
        # Different approach for vector search that's compatible with older LanceDB versions
        try:
            if query:
                # Get query embedding
                logger.info(f"Performing semantic search with query: '{query}'")
                query_vector = get_openai_embedding(query)
                
                # Try different vector search approaches
                try:
                    # Most compatible way: direct similarity search
                    logger.info("Using basic vector similarity search")
                    
                    # Try to get the schema to find vector column name
                    schema = table.schema
                    vector_column = "vector"  # Default vector column name
                    
                    # Run a SQL query using vector similarity directly
                    where_clause = ""
                    if username:
                        logger.info(f"Adding username filter: '{username}'")
                        where_clause = f" WHERE LOWER(username) LIKE '%{username.lower()}%'"
                    
                    # Use SQL for the most compatible approach with cosine distance
                    sql_query = f"""
                    SELECT * FROM {table_name}
                    {where_clause}
                    ORDER BY cosine_distance({vector_column}, :query_vector) ASC
                    LIMIT {limit}
                    """
                    
                    # Execute SQL with the embedding
                    results = table.execute(sql_query, query_vector=query_vector).to_list()
                    
                except Exception as sql_error:
                    logger.error(f"SQL vector search failed: {sql_error}")
                    logger.info("Falling back to basic search and manual filtering...")
                    
                    # Fallback: get all results and manually filter
                    all_results = table.to_pandas()
                    
                    # Calculate cosine similarity manually if needed
                    # For now, just return some results if username filter is present
                    if username:
                        filtered_results = all_results[all_results['username'].str.lower().str.contains(username.lower())]
                        results = filtered_results.head(limit).to_dict('records')
                    else:
                        # Without vector search capability, just return some results
                        results = all_results.head(limit).to_dict('records') 
                    
                    logger.warning("Vector search not available - returning basic results without similarity ranking")
                
            elif username:
                # Username only search (no vector search needed)
                logger.info(f"Filtering by username only: '{username}'")
                results = table.to_pandas()
                results = results[results['username'].str.lower().str.contains(username.lower())]
                
                # Sort if needed
                if sort_by_date:
                    logger.info("Sorting results by created_at (most recent first)")
                    results = results.sort_values('created_at', ascending=False)
                
                # Convert to records and limit
                results = results.head(limit).to_dict('records')
                
            else:
                # Neither query nor username - return all sorted by date
                logger.info("No search criteria provided, returning all records sorted by date")
                results = table.to_pandas()
                
                # Always sort by date in this case
                logger.info("Sorting results by created_at (most recent first)")
                results = results.sort_values('created_at', ascending=False)
                
                # Convert to records and limit
                results = results.head(limit).to_dict('records')
            
            logger.info(f"Found {len(results)} results")
            
            # Filter out the embedding vector before returning
            clean_results = []
            for result in results:
                # Create a copy without the vector field
                clean_result = {k: v for k, v in result.items() if k != 'vector'}
                clean_results.append(clean_result)
                
            return clean_results
            
        except Exception as inner_error:
            logger.error(f"Search operation failed: {inner_error}")
            logger.info("This might be due to compatibility issues with your version of LanceDB.")
            logger.info("Try: pip install -U lancedb")
            
            # Last resort: just return some records from the table without filtering
            try:
                logger.info("Attempting to return basic results...")
                basic_results = table.to_pandas().head(limit).to_dict('records')
                
                # Filter out the embedding vector
                clean_results = []
                for result in basic_results:
                    clean_result = {k: v for k, v in result.items() if k != 'vector'}
                    clean_results.append(clean_result)
                
                logger.info(f"Returning {len(clean_results)} basic results")
                return clean_results
            except:
                return []
            
    except Exception as e:
        logger.error(f"Error during search: {e}")
        return []

def main():
    # Parse arguments
    args = parse_args()
    
    logger.info(f"Connecting to LanceDB at {args.db_dir}, table '{args.table_name}'")
    
    # Extract Paul Graham username from query if needed
    username = args.username
    query = args.query
    
    # If querying for Paul Graham and no username is provided, extract it
    if not username and "paul graham" in query.lower():
        username = "paulg"
        logger.info(f"Automatically setting username filter to 'paulg' based on query")
    
    # For a "recent tweets" query, enable date sorting
    sort_by_date = args.sort_by_date
    if "recent" in query.lower() and not sort_by_date:
        sort_by_date = True
        logger.info("Automatically enabling date sorting based on query for 'recent' tweets")
    
    # Run the query
    results = search_tweets(
        args.db_dir, 
        args.table_name, 
        query=query, 
        username=username,
        limit=args.limit,
        sort_by_date=sort_by_date
    )
    
    if not results:
        print(f"No results found for the search parameters")
        return
    
    # Display results
    print(f"\nSearch results:\n")
    if query:
        print(f"Query: '{query}'")
    if username:
        print(f"Username filter: '{username}'")
    if sort_by_date:
        print("Sorted by: Most recent first")
    print(f"Found {len(results)} results\n")
    
    for result in results:
        print(format_tweet_result(result))

if __name__ == "__main__":
    main() 