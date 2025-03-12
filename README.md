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

### Viewing Stored Tweets

To view tweets stored in LanceDB:

```bash
uv run services/view_lancedb_data.py
```

## Wish List
- lance writer