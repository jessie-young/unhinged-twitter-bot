#!/usr/bin/env python3
import lancedb

# Connect to LanceDB
uri = "./data/lancedb"  # Adjust path if needed for local testing
db = lancedb.connect(uri)

# Check if the table exists
if "tweets" in db.table_names():
    print(f"Tables before deletion: {db.table_names()}")
    
    # Delete the table
    db.drop_table("tweets")
    print("'tweets' table deleted successfully")
    
    # Verify deletion
    print(f"Tables after deletion: {db.table_names()}")
else:
    print("No 'tweets' table found to delete") 