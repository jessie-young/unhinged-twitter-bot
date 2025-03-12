import redis
import yaml
from openai import OpenAI
import os

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

with open("personality.yaml", "r") as file:
    personality = yaml.safe_load(file)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_chain_of_thought(tweet, personality):
    prompt = f"""Given this tweet: "{tweet}"

You are an AI with the following personality:
Name: {personality['name']}
Traits: {', '.join(personality.get('traits', []))}
Current mood: {personality.get('mood', 'neutral')}

Think through how you would respond to this tweet, step by step.
First analyze the tweet, then consider your personality traits, and finally generate a response that matches your personality.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an AI agent responding to tweets. Think through your response step by step."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content

def process_tweet(tweet):
    try:
        chain_of_thought = generate_chain_of_thought(tweet, personality)

        response_prompt = f"""Based on the analysis, generate a tweet response as {personality['name']}.
        Tweet: {tweet}
        Personality: {personality}
        Make it concise and tweet-length appropriate."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generate a concise tweet response."},
                {"role": "user", "content": response_prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )

        final_response = response.choices[0].message.content

        final_output = f"""
Chain of Thought:
{chain_of_thought}

Final Response:
{personality['name']} says: {final_response}
"""
        return final_output

    except Exception as e:
        return f"Error processing tweet: {str(e)}"

def run_agent():
    while True:
        messages = r.xread({"tweet_stream": "$"}, count=1, block=5000)
        if messages:
            _, entries = messages[0]
            for _, data in entries:
                tweet = data["tweet"]
                response = process_tweet(tweet)

                with open("responses.txt", "a") as f:
                    f.write(response + "\n")

                print("Wrote tweet!")

if __name__ == "__main__":
    run_agent()
