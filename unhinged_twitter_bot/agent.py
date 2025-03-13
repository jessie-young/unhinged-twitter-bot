import json
import os
import uuid
from pathlib import Path

import redis
import yaml
from openai import OpenAI

from .activity_logging import AgentLogger, AgentSessionLogger
from .config import REDIS_EVENTS_PUBSUB_ADDR
from .twitter import TwitterAPI


class Agent:
    def __init__(self, personality_path: str | Path, check_cringe: bool = False, cringe_threshold: float = 0.7):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.redis = redis.Redis.from_url("redis://" + REDIS_EVENTS_PUBSUB_ADDR, decode_responses=True)

        # Load personality from file.
        with open(personality_path) as file:
            self.personality = yaml.safe_load(file)

        self.agent_name = self.personality["name"]
        self.logging = AgentLogger(self.agent_name, simulation_id=os.getenv("SIMULATION_ID", "anonymous-simulation"))
        self.twitter = TwitterAPI()

        # Cringe detection setup
        self.check_cringe = check_cringe
        if check_cringe:
            from .cringe_detector import CringeDetector

            self.cringe_detector = CringeDetector(threshold=cringe_threshold)

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

        logger.log_prompt("chain_of_thought", prompt, response.choices[0].message.content)

        return response.choices[0].message.content

    def generate_prompt(
        self,
        tweet: str,
        personality: dict,
        attempt_history: list[dict] | None = None,
        logger: AgentSessionLogger | None = None,
    ) -> str:
        """Dynamically generate a prompt based on previous attempts."""
        history_context = ""
        if attempt_history:
            history_context = "Previous attempts and their issues:\n" + "\n".join(
                f"- Response: '{attempt['response']}'\n"
                f"  Issue: {attempt['cringe_reason']} (cringe score: {attempt['cringe_score']})"
                for i, attempt in enumerate(attempt_history)
            )

        prompt = f"""You are crafting a response to a tweet. Your goal is to create a natural, authentic interaction 
that avoids common AI pitfalls like being too formal, trying too hard to be funny, or using forced internet speak.

TWEET TO RESPOND TO: "{tweet}"

RESPONDER'S PERSONALITY:
{personality}

{history_context if attempt_history else "This is the first attempt at responding."}

Create a prompt that will help generate a response with these guidelines:
1. Responses should feel natural and conversational, like something a real person would say
2. Avoid trying too hard to be clever or quirky
3. Stay true to the personality but don't overact it
4. Keep the tone casual and authentic
5. Don't use forced memes or try too hard to sound "internet-savvy"
6. The response should sound like it came from a real person who happens to have these interests/traits

Generate a prompt that will help create such a response. Focus on authenticity over performance."""

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at crafting natural, authentic social media interactions.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        logger.log_prompt("prompt_generation", prompt, response.choices[0].message.content)

        return response.choices[0].message.content

    def process_tweet(self, tweet, logger: AgentSessionLogger):
        try:
            max_attempts = 10 if self.check_cringe else 1
            attempt = 0
            lowest_cringe_score = float("inf")
            best_response = None
            attempt_history = []

            while attempt < max_attempts:
                # Generate dynamic prompt based on history
                prompt = self.generate_prompt(tweet, self.personality, attempt_history, logger)

                # Generate response using the dynamic prompt
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an AI agent responding to tweets."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=100,
                )

                final_response = response.choices[0].message.content
                logger.log_prompt("tweet_generation", prompt, final_response)

                if self.check_cringe:
                    is_cringe, score, reason = self.cringe_detector.is_cringe(final_response)
                    logger.log_prompt("cringe_check", final_response, f"Score: {score}, Reason: {reason}")

                    # Store attempt history
                    attempt_history.append(
                        {
                            "chain_of_thought": prompt,
                            "response": final_response,
                            "cringe_score": score,
                            "cringe_reason": reason,
                        }
                    )

                    # Keep track of the least cringe response
                    if score < lowest_cringe_score:
                        lowest_cringe_score = score
                        best_response = final_response

                    if is_cringe:
                        print(f"Response was cringe (score: {score}): {reason}")
                        if attempt < max_attempts - 1:
                            print("Generating new prompt based on feedback...")
                            attempt += 1
                            continue
                        print(f"Max attempts reached, using least cringe response (score: {lowest_cringe_score})")
                        final_response = best_response
                    else:
                        print(f"Response passed cringe check (score: {score})")
                    break
                else:
                    break

                attempt += 1

            return final_response

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
        logger.log_prompt("tweet_relevance", prompt, result)
        is_relevant = result.upper().startswith("YES")
        explanation = result.split(":", 1)[1].strip() if ":" in result else result

        return is_relevant, explanation

    def run_agent(self):
        for tweet_str in self.twitter.get_tweets():
            try:
                # Safely handle the tweet string by encoding/decoding with error handling.
                tweet_str = tweet_str.encode("utf-8", errors="ignore").decode("utf-8")
                tweet_data = json.loads(tweet_str)

                # Skip if the tweet is from ourself.
                if tweet_data["author"] == self.agent_name:
                    print(f"Skipping own tweet from {tweet_data['author']}")
                    continue

                with self.logging.session_logger(self.agent_name + "_" + str(uuid.uuid4())) as logger:
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
