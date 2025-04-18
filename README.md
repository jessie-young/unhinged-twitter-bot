# Unhinged Twitter Bot

A Twitter bot system that processes tweets, generates embeddings, and stores them in LanceDB for semantic search.

## Getting Started

### Running the Services

To start all services, run:

```bash
docker-compose up
```

If you've made changes to the code or Dockerfile, use the `--build` flag to rebuild the containers:

```bash
docker-compose up --build
```

This will start:
- Redis for message passing (events-pubsub)
- Tweet embedding service (processes tweets and adds them to LanceDB)

### Running Simulation

```bash
uv run simulate test_simulation --tweets-file data/simulation_tweets/some_startup_tweets.txt --seed-memory-id startups
```

### Testing the System

#### Option 1: Send a test tweet directly to Redis

This command publishes a tweet directly to the Redis 'tweets' channel:

```bash
docker exec -it unhinged-twitter-bot-events-pubsub-1 redis-cli PUBLISH tweets '{"author":"test_user","content":"This is a test tweet sent directly to Redis"}'
```

#### Option 2: Use the test publisher with additional metadata

For testing with additional tweet metadata (like retweets and likes):

```bash
uv run scripts/test_tweet_publisher.py --username username --text "Your tweet content here"
```

### Collecting Twitter Data

You can use the Twitter data collector script to fetch tweets from the Twitter API based on specific topics or from specific Twitter accounts.

#### Setup Twitter API Access

1. Create a Twitter Developer account at https://developer.twitter.com/
2. Create a project and app to get API keys
3. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```
4. Edit the `.env` file to add your Twitter API bearer token:
   ```
   TWITTER_BEARER_TOKEN=your_actual_bearer_token_here
   ```

#### Running the Collector

The collector script supports two modes:
- **Topics mode**: Collect tweets matching specific search queries
- **Authors mode**: Collect tweets from specific Twitter accounts

##### Basic Usage:

```bash
# Default mode (topics)
python data/twitter_data_collector.py 

# Author mode with default authors
python data/twitter_data_collector.py --mode authors
```

##### Twitter API Rate Limits

The script implements rate limit handling to avoid Twitter API errors:
- Free tier limits: 450 requests per 15-minute window for search, 300 requests for user timelines
- The script spaces out requests and will automatically wait when approaching limits

##### Example: Collecting Startup-Related Tweets (Topics Mode)

To collect tweets related to startups, founders, and venture capital:

```bash
uv run data/twitter_data_collector.py --mode topics --topics "startup OR founder OR entrepreneur OR \"Y Combinator\" OR YC OR VC OR funding OR \"Series A\" OR \"Series B\" -is:retweet lang:en"
```

##### Example: Collecting Tweets from Specific Authors

To collect tweets from specific Twitter accounts:

```bash
uv run data/twitter_data_collector.py --mode authors --authors paulg garrytan ycombinator
```

By default, the collector will fetch tweets from these tech/VC Twitter accounts if no authors are specified:
- paulg (Paul Graham)
- sama (Sam Altman)
- naval (Naval Ravikant)
- jason (Jason Calacanis)
- eladgil (Elad Gil)
- garrytan (Garry Tan)
- ycombinator (Y Combinator)
- techcrunch (TechCrunch)
- a16z (Andreessen Horowitz)
- sequoia (Sequoia Capital)

**Important Notes**: 
- When specifying query terms with spaces, use double quotes around phrases
- Don't use the @ symbol when specifying Twitter usernames
- The collected data will be saved to the `data/datasets` directory by default

##### Additional Options

```bash
# Set maximum number of tweets per topic/author (10-100)
--max-results 50

# Set output directory
--output-dir data/my_datasets

# Set custom output filename
--output-file my_tweets.json

# Limit the number of API requests (to stay under rate limits)
--max-requests 20
```

### Viewing Stored Tweets

To view tweets stored in LanceDB:

```bash
uv run services/view_lancedb_data.py
```

## Loading Seed Data

The project includes a data loading script that can be used to populate the LanceDB database with tweets from JSON files. This is useful for creating seed data as a starting point for simulations.

### Loading Twitter Data

To load Twitter data into the vector database, use the `load_data.py` script:

```bash
# Load startup-related tweets from the JSON file into a table named 'tweets'
uv run seed --input-files data/datasets/twitter_data_20250312_164318.json data/datasets/topics_data_20250313_145824.json data/datasets/authors_data_20250313_151002.json --db-uri data/seed --table-name tweets
```

#### Parameters:

- `--input-json`: Path to the JSON file containing the tweets
- `--db-uri`: Directory where the LanceDB database will be stored (in this example, `data/seed`)
- `--table-name`: Name of the table to create in the database (default: 'tweets')

The script will:
1. Load the tweets from the JSON file
2. Process and embed them using the BAAI/bge-small-en-v1.5 model
3. Store them in a LanceDB table at the specified location
4. Display a summary of the loaded data

Once loaded, the seed data will be available at the specified `--db-uri` location and can be accessed by the application for similarity searches or other operations.

## Wish List
- lance writer