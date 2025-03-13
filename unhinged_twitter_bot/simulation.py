import subprocess
import dataclasses

from unhinged_twitter_bot.twitter import TwitterAPI


@dataclasses.dataclass(frozen=True)
class SimulationSeed:
    history_db_seed_name: str
    simulation_event_stream: list[str]


def run_simulation(seed: SimulationSeed):
    api = TwitterAPI()

    for tweet in seed.simulation_event_stream:
        api.make_tweet(content=tweet, author="simulator")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run a Twitter bot simulation')
    parser.add_argument('--history-db-name', required=True, help='Name of the history database seed')
    parser.add_argument('--tweets', nargs='+', required=True, help='List of tweets to simulate')

    args = parser.parse_args()

    seed = SimulationSeed(
        history_db_seed_name=args.history_db_name,
        simulation_event_stream=args.tweets
    )

    run_simulation(seed)
