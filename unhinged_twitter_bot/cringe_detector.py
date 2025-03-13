import os

import instructor
import pydantic
from openai import OpenAI


class CringeLevel(pydantic.BaseModel):
    score: float
    reason: str


class CringeDetector:
    def __init__(self, threshold: float = 0.7):
        self.client = instructor.from_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
        self.threshold = threshold

    def analyze(self, tweet: str) -> tuple[float, str]:
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=CringeLevel,
            messages=[
                {
                    "role": "user",
                    "content": f"Rate this tweet on level of cringeness, from 0 to 1 and provide a concise reason as to why:\n\n{tweet}",
                },
            ],
            temperature=0.7,
        )
        return response.score, response.reason

    def is_cringe(self, tweet: str) -> tuple[bool, float, str]:
        score, reason = self.analyze(tweet)
        return score > self.threshold, score, reason
