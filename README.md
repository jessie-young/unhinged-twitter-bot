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
- Batch ingest subscriber service
- Tweet embedding service (processes tweets and adds them to LanceDB)

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

You can use the Twitter data collector script to fetch tweets from the Twitter API based on specific topics.

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

Basic usage:

```bash
python data/twitter_data_collector.py
```

#### Example: Collecting Startup-Related Tweets

To collect tweets related to startups, founders, and venture capital:

```bash
python data/twitter_data_collector.py --topics "startup OR founder OR entrepreneur OR \"Y Combinator\" OR YC OR VC OR funding OR \"Series A\" OR \"Series B\" -is:retweet lang:en"
```

**Important Note**: When specifying query terms with spaces, use double quotes around phrases. The Twitter API will reject queries with single quotes.

The collected data will be saved to the `data/datasets` directory by default.

### Viewing Stored Tweets

To view tweets stored in LanceDB:

```bash
uv run services/view_lancedb_data.py
```

## Wish List
- lance writer