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


def run_simulation(seed: SimulationSeed, build: bool):
    print("Spinning up simulation world...")
    env = {
        "LANCEDB_TABLE_NAME": seed.seed_memory_id,
        "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        "PATH": os.environ["PATH"],
        "SIMULATION_ID": seed.simulation_id,
    }
    proc = subprocess.Popen([
        "docker-compose",
        "up",
        "-d",
        *([] if build else ["--build"]),
    ],
    env=env)

    try:
        # Wait for all services to be up
        while True:
            result = subprocess.run(["docker-compose", "ps", "--format", "json"], env={"PATH": os.environ["PATH"]}, text=True, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError("Failed to check Docker services status")

            if result.stdout != "":
                services = [s for s in result.stdout.split("\n") if s != ""]
                all_running = all(
                    '"State":"running"' in service
                    for service in services
                )
                
                if all_running:
                    print("All services are up and running!")
                    break

            print("Waiting for services to start...")
            time.sleep(2)

        # Maker the tweets
        time.sleep(8)
        api = TwitterAPI()
        for tweet in seed.simulation_event_stream:
            api.make_tweet(content=tweet, author="simulator")

        # Follow logs in real-time
        log_process = subprocess.call(
            ["docker-compose", "logs", "-f"],
            env=env,
            text=True,
        )

        time.sleep(999999999)
    finally:
        subprocess.call(["docker-compose", "down"])


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run a Twitter bot simulation')
    parser.add_argument("simulation_id", help="Unique identifier for the simulation run")
    parser.add_argument("--tweets-file", required=True, help="txt file containing tweets to simulate")
    parser.add_argument("--seed-memory-id", required=True, help="Unique identifier for the memory to seed the simulation with")
    parser.add_argument("--build", action="store_true", help="Rebuild the containers")

    args = parser.parse_args()

    with open(args.tweets_file, "r") as f:
        tweets = f.readlines()

    seed = SimulationSeed(
        simulation_id=args.simulation_id,
        seed_memory_id=args.seed_memory_id,
        simulation_event_stream=tweets,
    )

    run_simulation(seed, args.build)
