# Scripts to run

## Events

Interacting with the events service: this is the service that represents our world state. It will be able to:

1. Manually ingest a new event `uv run scripts/events.py make-tweet --author jaychia -- This is an example tweet`
2. Start a bunch of bots to simulate tweets `uv run scripts/events.py simulate-tweets`
