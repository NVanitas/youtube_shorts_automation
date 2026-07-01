import sys, os
sys.path.insert(0, r"c:\Py\youtube_shorts_automation")
os.chdir(r"c:\Py\youtube_shorts_automation")

import json
from pathlib import Path

# Load config
from config import NICHES, OUTPUT_DIR
from script_generator import generate_script

os.environ["GEMINI_API_KEY"] = "BAD_KEY"
video_dir = OUTPUT_DIR / "test_fallback"
video_dir.mkdir(exist_ok=True)

try:
    data = generate_script("facts", video_dir)
    print("RETURNED DATA:", type(data))
    if data:
        print("KEYS:", data.keys())
except Exception as e:
    import traceback
    traceback.print_exc()
