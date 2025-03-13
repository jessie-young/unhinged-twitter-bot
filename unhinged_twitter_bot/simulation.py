import os
import subprocess
import dataclasses
import json
import time

from unhinged_twitter_bot.twitter import TwitterAPI


@dataclasses.dataclass(frozen=True)
class SimulationSeed:
    simulation_id: str
    seed_memory_id: str
    simulation_event_stream: list[str]


def run_simulation(seed: SimulationSeed):
    print("Spinning up simulation world...")
    proc = subprocess.Popen([
        "docker-compose",
        "up",
        "-d",
        # "--build",
    ],
    env={
        "LANCEDB_TABLE_NAME": seed.seed_memory_id,
        "PATH": os.environ["PATH"],
    })

    try:
        while True:
            result = subprocess.run(["docker-compose", "ps", "--format", "json"], env={"PATH": os.environ["PATH"]}, text=True, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError("Failed to check Docker services status")

            if result.stdout != "":
                # Parse JSON output to check service status
                services = [s for s in result.stdout.split("\n") if s != ""]
                
                # Check if all services are running
                all_running = all(
                    '"State":"running"' in service
                    for service in services
                )
                
                if all_running:
                    print("All services are up and running!")
                    break

            print("Waiting for services to start...")
            time.sleep(2)  # Wait 2 seconds before checking again

        api = TwitterAPI()

        for tweet in seed.simulation_event_stream:
            api.make_tweet(content=tweet, author="simulator")

        time.sleep(999999999)
    finally:
        subprocess.call(["docker-compose", "down"])


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run a Twitter bot simulation')
    parser.add_argument("simulation_id", help="Unique identifier for the simulation run")
    parser.add_argument("--tweets-file", required=True, help="txt file containing tweets to simulate")
    parser.add_argument("--seed-memory-id", required=True, help="Unique identifier for the memory to seed the simulation with")

    args = parser.parse_args()

    with open(args.tweets_file, "r") as f:
        tweets = f.readlines()

    seed = SimulationSeed(
        simulation_id=args.simulation_id,
        seed_memory_id=args.seed_memory_id,
        simulation_event_stream=tweets,
    )

    run_simulation(seed)
