#!/usr/bin/env python3
import lancedb
import pandas as pd
import argparse

def view_lancedb_data(uri="./data/lancedb", limit=100, include_vectors=False):
    """
    View data stored in the LanceDB tweets table
    
    Args:
        uri: Path to LanceDB directory
        limit: Maximum number of records to retrieve
        include_vectors: Whether to include the vector embeddings in the output
    """
    print(f"Connecting to LanceDB at {uri}")
    db = lancedb.connect(uri)
    
    if "tweets" not in db.table_names():
        print("No 'tweets' table found in the database")
        print(f"Available tables: {db.table_names()}")
        return
    
    table = db.open_table("tweets")
    print(f"Successfully opened 'tweets' table")
    
    # Query all data
    print(f"\nRetrieving up to {limit} records...")
    
    # Use proper LanceDB query syntax
    query = table.search("*").limit(limit)
    df = query.to_pandas()
    
    if not include_vectors and "vector" in df.columns:
        df = df.drop(columns=["vector"])
    
    if len(df) == 0:
        print("No data found in the table")
        return
    
    print(f"\nRetrieved {len(df)} records:")
    print(df)
    
    # Print a few sample records with more details
    print("\nSample Records (detailed view):")
    for i, row in df.head(min(3, len(df))).iterrows():
        print(f"\nRecord #{i+1}:")
        for col, val in row.items():
            if col != "vector":  # Skip vector to keep output clean
                print(f"  {col}: {val}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='View data from LanceDB tweets table')
    parser.add_argument('--uri', type=str, default='./data/lancedb', 
                        help='Path to LanceDB directory')
    parser.add_argument('--limit', type=int, default=100,
                        help='Maximum number of records to retrieve')
    parser.add_argument('--include-vectors', action='store_true',
                        help='Include vector embeddings in the output')
    
    args = parser.parse_args()
    view_lancedb_data(args.uri, args.limit, args.include_vectors) 