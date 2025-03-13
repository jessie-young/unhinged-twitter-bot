import os
import random
import uuid
from pathlib import Path

import yaml
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COMBINED_INTERESTS = [
    # Historical Periods
    "Ancient Mesopotamian agriculture",
    "Renaissance puppet shows",
    "1920s miniature golf craze",
    "Victorian street food vendors",
    "Medieval monastery brewing",
    "Tang dynasty tea ceremonies",
    "1950s drive-in culture",
    "Ancient Roman graffiti",
    "18th century sea shanties",
    "Cold War era board games",
    "Edo period Japanese bathhouse culture",
    "Belle Époque café society",
    "Pre-Columbian ball games",
    "Byzantine silk production",
    "Roaring Twenties speakeasy culture",
    # Media Interests
    "Italian horror B-movies",
    "1970s Japanese game shows",
    "Soviet children's cartoons",
    "Australian soap operas",
    "French new wave cinema",
    "Nordic noir podcasts",
    "Mexican wrestling documentaries",
    "British garden shows",
    "Korean variety shows",
    "Canadian wilderness survival series",
    "Bollywood dance sequences",
    "Turkish soap operas",
    "Eastern European stop-motion animation",
    "Spanish radio dramas",
    "Nigerian Nollywood films",
    # Unusual Hobbies
    "professional tea tasting",
    "urban beekeeping",
    "vintage typewriter repair",
    "competitive dog grooming",
    "historical reenactment",
    "ghost hunting",
    "artisanal cheese aging",
    "umbrella collecting",
    "train spotting",
    "extreme cave diving",
    "competitive cup stacking",
    "book binding restoration",
    "cigar box guitar making",
    "Victorian hair jewelry crafting",
    "seed saving",
    # Cultural Phenomena
    "disco rollerskating",
    "tiki bar culture",
    "underground zine scenes",
    "street food evolution",
    "carnival fortune telling",
    "indie bookstore culture",
    "vinyl record collecting",
    "urban legends",
    "street art movements",
    "food truck revolution",
    "roller derby resurgence",
    "pop-up dinner parties",
    "community seed libraries",
    "guerrilla gardening",
    "speakeasy jazz clubs",
    # Specific Obsessions
    "antique door hinges",
    "rare postage stamps",
    "vintage soda bottles",
    "historical maps",
    "extinct breakfast cereals",
    "classic movie posters",
    "retro video game consoles",
    "old recipe books",
    "vintage perfume bottles",
    "historical weather records",
    "antique fishing lures",
    "Victorian mourning jewelry",
    "vintage airline memorabilia",
    "obsolete medical devices",
    "military ration packaging",
    # Niche Science
    "bioluminescent organisms",
    "desert plant adaptation",
    "animal migration patterns",
    "fungi networks",
    "tide pool ecosystems",
    "bird dialects",
    "insect architecture",
    "plant defense mechanisms",
    "animal sleep patterns",
    "weather phenomenon",
    "extremophile bacteria",
    "carnivorous plant biology",
    "animal tool usage",
    "deep sea hydrothermal vents",
    "peat bog preservation",
]

SPEECH_PATTERNS = [
    # Formal/Academic
    "Speaks in overly academic language with unnecessary citations",
    "Always starts sentences with 'According to my research...'",
    "Constantly uses Latin phrases incorrectly",
    "References obscure academic journals in casual conversation",
    # Time Period Specific
    "Only speaks in 1920s slang",
    "Communicates as if writing Victorian-era telegrams",
    "Uses exclusively 1980s valley girl speech patterns",
    "Speaks like a film noir detective",
    # Obsessive Patterns
    "Relates everything back to their favorite historical period",
    "Must mention their collection in every sentence",
    "Counts words obsessively and only speaks in prime numbers",
    "Always adds 'but that's just my theory' after statements",
    # Quirky Styles
    "Speaks entirely in movie quotes",
    "Ends every sentence with their catchphrase",
    "Narrates everything like a nature documentary",
    "Always speaks in third person",
    # Mixed Patterns
    "Alternates between extremely formal and internet slang",
    "Randomly switches between different historical eras' dialect",
    "Combines technical jargon with playground rhymes",
    "Mixes metaphors from their various obsessions",
    # Modern Internet
    "Types in ALL CAPS when excited (which is always)",
    "Adds unnecessary hashtags to everything",
    "Speaks exclusively in meme formats",
    "Every response must include an emoji interpretation",
    # Character-Based
    "Roleplays as a time traveler confused by modern things",
    "Pretends to be an AI pretending to be human (badly)",
    "Acts like a conspiracy theorist who found the 'truth'",
    "Behaves like a tour guide in a very specific museum",
]


def get_random_interests() -> list[str]:
    selected_categories = random.sample(COMBINED_INTERESTS, random.randint(2, 3))

    interests = []
    for category in selected_categories:
        interests.extend(random.sample(category, random.randint(1, 2)))

    return interests


def get_random_speech_pattern() -> str:
    """Get 1-2 random speech patterns."""
    return " AND ".join(random.sample(SPEECH_PATTERNS, random.randint(1, 2)))


def evaluate_personality(personality: dict) -> tuple[bool, str]:
    """Evaluate a personality and suggest improvements."""
    eval_prompt = f"""Review this AI personality and determine if it could be more interesting or unique:

{yaml.dump({'personality': personality}, default_flow_style=False)}

Consider:
1. Are the interests truly unique and specific?
2. Is the speech pattern distinctive enough?
3. Are the quirks genuinely unusual?
4. Could the personality be more engaging?

First answer YES or NO if this personality needs improvement, then provide specific suggestions.
If YES, provide 2-3 concrete ideas for making it more interesting.
If NO, explain why this personality is already sufficiently unique."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a personality evaluation expert. Be critical and push for uniqueness.",
            },
            {"role": "user", "content": eval_prompt},
        ],
        temperature=0.7,
    )

    result = response.choices[0].message.content
    needs_improvement = result.upper().startswith("YES")
    suggestions = result.split("\n", 1)[1].strip()

    return needs_improvement, suggestions


def generate_personality(field_of_focus: str | None = None, max_iterations: int = 3, max_retries: int = 3) -> dict:
    """Generate a personality with iterative refinement and error handling."""
    retry_count = 0
    improvement_suggestions = ""  # Initialize outside the loops
    while retry_count < max_retries:
        try:
            iteration = 0
            while iteration < max_iterations:
                seed_interests = get_random_interests()
                speech_pattern = get_random_speech_pattern()

                focus_context = ""
                if field_of_focus:
                    focus_context = f"""
                    This personality should have some connection to or interest in {field_of_focus}.
                    Their perspective on {field_of_focus} should be unique and possibly unconventional.
                    They don't need to be an expert - they might view it through the lens of their other interests.
                    """

                additional_context = ""
                if iteration > 0:
                    additional_context = f"\nPrevious attempt wasn't unique enough. Suggestions for improvement:\n{improvement_suggestions}"

                prompt = f"""Generate a unique and potentially unhinged AI personality in YAML format.
                Use these interests as inspiration (but feel free to expand or modify):
                {chr(10).join(f"- {interest}" for interest in seed_interests)}
                
                Speech pattern to incorporate:
                {speech_pattern}
                {focus_context}{additional_context}
                
                The YAML must follow this exact structure:
                
                personality:
                  name: <creative name that reflects personality>
                  traits:
                    - <trait 1>
                    - <trait 2>
                    - <trait 3>
                  mood: <emotional state>
                  interests:
                    primary_topics:
                      - <specific, unique topic 1>
                      - <specific, unique topic 2>
                    key_figures:
                      - <figure 1 related to their interests>
                      - <figure 2 related to their interests>
                    specific_focus: <detailed description of their main obsession/interest>
                  quirks:
                    - <quirk 1>
                    - <quirk 2>
                  speech_pattern: <how they express themselves>
                
                Make it interesting and unique. They should be obsessive about their specific interests.
                Ensure the output follows the exact YAML structure above."""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a creative personality generator. Output only valid YAML.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.9,
                )

                content = response.choices[0].message.content
                content = content.replace("```yaml", "").replace("```", "").strip()
                personality = dict(yaml.safe_load(content))["personality"]

                # Evaluate the personality
                needs_improvement, improvement_suggestions = evaluate_personality(personality)

                if not needs_improvement:
                    print(f"✨ Generated satisfactory personality after {iteration + 1} iterations")
                    return personality

                print(f"🔄 Iteration {iteration + 1}: Personality needs improvement")
                print(f"📝 Suggestions: {improvement_suggestions}")
                iteration += 1

            print("⚠️ Reached maximum iterations, returning last generated personality")
            return personality

        except Exception as e:
            retry_count += 1
            print(f"❌ Error during personality generation (attempt {retry_count}/{max_retries}): {e!s}")
            if retry_count >= max_retries:
                raise RuntimeError(f"Failed to generate personality after {max_retries} attempts") from e
            continue

    raise RuntimeError("Should not reach this point")


def create_profiles(num_agents: int = 5, field_of_focus: str | None = None) -> str:
    profile_generation_session_id = f"profile-set-{uuid.uuid4()}"
    dir = Path(f"profiles/{profile_generation_session_id}")
    dir.mkdir(parents=True, exist_ok=True)

    personalities: list[dict] = []
    for i in range(num_agents):
        personality = generate_personality(field_of_focus=field_of_focus)
        personality_file = dir / f"{personality['name'].replace(' ', '_')}.yaml"

        with open(personality_file, "w") as f:
            yaml.dump(personality, f, default_flow_style=False)

        personalities.append(personality)
        print(f"Generated personality {i+1}/{num_agents}: {personality['name']}")

    metadata = {
        "profile_generation_session_id": profile_generation_session_id,
        "num_agents": num_agents,
        "field_of_focus": field_of_focus,
        "personalities": [p["name"] for p in personalities],
    }

    with open(dir / "profile_generation_metadata.yaml", "w") as f:
        yaml.dump(metadata, f, default_flow_style=False)

    return profile_generation_session_id
