import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
BACKGROUNDS_DIR = BASE_DIR / "assets" / "backgrounds"
MUSIC_DIR = BASE_DIR / "assets" / "music"

# Create directories if they do not exist
for directory in [OUTPUT_DIR, BACKGROUNDS_DIR, MUSIC_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Niches Configuration
NICHES = {
    "facts": {
        "name": "Kids Curiosities",
        "voice": "en-US-AnaNeural",  # Cute, youthful kid cartoon voice
        "rate": "+8%",               # Paced for curious storytelling
        "pitch": "+0Hz",             # Natural youthful pitch
        "music_theme": "upbeat",
        "font_name": "Impact",       # Bold, punchy font
        "primary_color": "FFFFFF",   # White (RGB Hex)
        "highlight_color": "FFFF00", # Bright Yellow (RGB Hex)
        "outline_color": "000000",   # Black (RGB Hex)
        "font_size": 80,             # Decreased from 100 to prevent mobile screen overflow
        "alignment": 2,              # Centered bottom in ASS
        "margin_v": 350,             # Vertical margin to position subtitles higher (out of player UI)
        "prompt_template": """
Create a viral, highly engaging, educational, and fun YouTube Shorts script in English for curious kids and general audiences about mind-blowing bizarre nature, freaky deep sea creatures, animal superpowers, or strange earth mysteries.
You MUST respond with a raw JSON object ONLY, containing exactly three keys: "title", "script", and "scenes".

JSON Format:
{
  "title": "A viral, curiosity-driven YouTube Short title in English with 1 emoji (e.g. The Real Monsters Living Inside Deep Sea Volcanoes! 🌋)",
  "script": "The full voiceover script text",
  "scenes": [
    {
      "keyword": "a 2-4 word visual search term for stock video footage (e.g. deep sea volcanic vent, glowing anglerfish mouth, giant squid eye)",
      "reaction": "one of: shocked | scared | thinking | excited | mindblown | curious | crying | waving"
    }
  ]
}

RULES for "title":
- Focus on bizarre, mysterious, or shocking nature facts (deep sea monsters, weird animal biology, strange natural phenomena).
- Make it impossible to scroll past. Include 1 relevant emoji.

RULES for "script":
- Keep it under 65-75 words so it fits in a fast-paced 16-20 second video.
- The script MUST follow this winning structure:
  1. INSTANT HOOK (0-2s): A shocking question or claim that grabs attention immediately (e.g. "Did you know real-life monsters are swimming right beneath us?").
  2. 2 PUNCHY BIZARRE FACTS: Vivid analogies (e.g. "pressure like an elephant stepping on your thumb", "shoots pure boiling acid").
  3. INTERACTIVE QUESTION + SEAMLESS LOOP ENDING: Ask a direct engaging question (e.g. "Which of these bizarre creatures would scare you the most? Drop your answer below and subscribe because...") that flows smoothly back to the first word of the hook!
- Use plain text only. No markdown, no emojis in script, no speaker names, no stage directions.

RULES for "scenes":
- You must generate exactly 6-7 scenes to cover the video duration (each scene plays for ~2.5 - 3 seconds).
- For each scene, specify:
  - "keyword": a short, specific stock video search term describing the visual action at that moment (e.g. "deep sea hydrothermal vent", "glowing jellyfish tentacles", "dark underwater trench").
  - "reaction": MUST be exactly one of: shocked, scared, thinking, excited, mindblown, curious, crying, waving.
"""
    },
    "stoicism": {
        "name": "Stoic Wisdom & Motivation",
        "voice": "en-GB-RyanNeural",  # Deep, British male voice
        "rate": "+0%",               # Normal pacing for philosophical tone
        "music_theme": "mysterious",
        "font_name": "Georgia",      # Elegant serif font
        "primary_color": "F0F0F0",   # Off-white (RGB Hex)
        "highlight_color": "FFD700", # Deep Gold (RGB Hex)
        "outline_color": "0F0F0F",   # Dark outline
        "font_size": 80,             # Decreased from 100 to prevent mobile screen overflow
        "alignment": 2,              # Centered bottom in ASS
        "margin_v": 350,             # Vertical margin to position subtitles higher (out of player UI)
        "prompt_template": """
Create a deep, motivational, and philosophical YouTube Shorts script in English about Stoicism or ancient wisdom.
You MUST respond with a raw JSON object ONLY, containing exactly three keys: "title", "script", and "keywords".

JSON Format:
{{
  "title": "A deep, powerful, viral YouTube Short title in English with 1 emoji (max 65 chars)",
  "script": "The full voiceover script text",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"]
}}

RULES for "title":
- Make it deep, thought-provoking, or impactful to drive clicks and engagement. Include 1 relevant emoji.

RULES for "script":
- Keep it under 110 words so it fits in a 45-55 second video.
- The script MUST follow this structure:
  1. A deep, reflective, paradoxical HOOK that makes the viewer stop scrolling (e.g. "What is destroying your peace, is exactly what will save you.").
  2. 2-3 short, powerful lessons or quotes and how they apply to modern life.
  3. A short engagement question before the end to trigger comments and likes (e.g., "Which lesson do you need most today? Comment below and subscribe!").
  4. A PERFECT LOOP ENDING. The final sentence must seamlessly connect back to the first word of the hook! For example, end with "You must always remember that..." leading straight back into the hook.
- Use plain text only. No markdown, no emojis, no asterisks, no speaker names, no stage directions.

RULES for "keywords":
- It must contain exactly 15 keywords or short 1-2 word search terms in English.
- The keywords should strictly match the chronological progression of the stoic voiceover so that every 3 seconds a new highly relevant image can be shown.
"""
    }
}

# General Subtitle ASS Style template
ASS_STYLE_TEMPLATE = """[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 1138
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00{primary_colour},&H00CCCCCC,&H00{outline_colour},&H00000000,-1,0,0,0,100,100,0,0,1,6,3,{alignment},20,20,{margin_v},1
Style: Highlight,{font_name},{font_size},&H00{highlight_colour},&H00CCCCCC,&H00{outline_colour},&H00000000,-1,0,0,0,100,100,0,0,1,6,3,{alignment},20,20,{margin_v},1
"""
