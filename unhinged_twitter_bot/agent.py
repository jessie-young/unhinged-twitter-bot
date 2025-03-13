import json
import os
import uuid
from pathlib import Path

import redis
import yaml
from openai import OpenAI

from .activity_logging import AgentLogger, AgentSessionLogger
from .twitter import TwitterAPI


class Agent:
    def __init__(self, personality_path: str | Path):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.redis = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Load personality from file.
        with open(personality_path) as file:
            self.personality = yaml.safe_load(file)

        self.agent_name = self.personality["name"]
        self.logging = AgentLogger(self.agent_name)
        self.twitter = TwitterAPI()

    def generate_chain_of_thought(self, tweet, logger: AgentSessionLogger):
        prompt = f"""Given this tweet: "{tweet}"

You are an AI with the following personality:
Name: {self.personality['name']}
Traits: {', '.join(self.personality.get('traits', []))}
Current mood: {self.personality.get('mood', 'neutral')}

Think through how you would respond to this tweet, step by step.
First analyze the tweet, then consider your personality traits, and finally generate a response that matches your personality.
We want to make high quality responses that are interesting and tend to get lots of engagement.
"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI agent responding to tweets. Think through your response step by step.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        logger.log_prompt(prompt, response.choices[0].message.content)

        return response.choices[0].message.content

    def process_tweet(self, tweet, logger: AgentSessionLogger):
        try:
            chain_of_thought = self.generate_chain_of_thought(tweet, logger)

            response_prompt = f"""Based on the analysis, generate a tweet response as {self.personality['name']}.
            Tweet: {tweet}
            Personality: {self.personality}
            Make it tweet-length appropriate and interesting."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate a tweet response."},
                    {"role": "user", "content": response_prompt},
                ],
                temperature=0.7,
                max_tokens=100,
            )

            final_response = response.choices[0].message.content
            logger.log_prompt(response_prompt, final_response)
            final_output = f"""
Chain of Thought:
{chain_of_thought}

Final Response:
{self.personality['name']} says: {final_response}
"""
            return final_output

        except Exception as e:
            return f"Error processing tweet: {e!s}"

    def is_tweet_relevant(self, tweet: str, logger: AgentSessionLogger) -> tuple[bool, str]:
        """Determine if a tweet is relevant to the agent's interests."""
        prompt = f"""Given this tweet: "{tweet}"

You are an AI with the following interests:
{self.personality.get('interests', 'No specific interests')}

Determine if this tweet is relevant to your interests. Think step by step:
1. What is the main topic of the tweet?
2. Does it relate to any of your interests?
3. How strongly does it align with your interests?

        Respond with either YES or NO, followed by a brief explanation.
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You must respond with either 'YES: <explanation>' or 'NO: <explanation>'",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        result = response.choices[0].message.content
        logger.log_prompt(prompt, result)
        is_relevant = result.upper().startswith("YES")
        explanation = result.split(":", 1)[1].strip() if ":" in result else result

        return is_relevant, explanation

    def run_agent(self):
        for tweet_str in self.twitter.get_tweets():
            with self.logging.session_logger(self.agent_name + "_" + str(uuid.uuid4())) as logger:
                try:
                    # Safely handle the tweet string by encoding/decoding with error handling.
                    tweet_str = tweet_str.encode("utf-8", errors="ignore").decode("utf-8")
                    tweet_data = json.loads(tweet_str)

                    # Skip if the tweet is from ourself.
                    if tweet_data["author"] == self.agent_name:
                        print(f"Skipping own tweet from {tweet_data['author']}")
                        continue

                    # Check if the tweet is relevant to our interests.
                    is_relevant, explanation = self.is_tweet_relevant(tweet_data["content"], logger)
                    if not is_relevant:
                        print(f"Skipping irrelevant tweet: {explanation}")
                        continue

                    print(f"Processing relevant tweet: {explanation}")
                    response = self.process_tweet(tweet_data["content"], logger)
                    # Ensure response is also properly encoded.
                    response = response.encode("utf-8", errors="ignore").decode("utf-8")
                    self.twitter.make_tweet(response, self.personality["name"])
                    print(f"Responded to tweet from {tweet_data['author']}!")

                except Exception as e:
                    print(f"Error processing tweet data: {e!s}")
                    continue
