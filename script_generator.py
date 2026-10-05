import os
import sys
import json
import re
import random
import difflib
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 on Windows to support console emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from config import NICHES

# Load environment variables
load_dotenv()

# Initialize Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "sua_chave_do_gemini_aqui":
    genai.configure(api_key=api_key)
else:
    print("WARNING: GEMINI_API_KEY not found or is default placeholder in environment. Please add it to your .env file.")

# Large subject pools for Nicosaurus (Dinos & Abyss). Subtopics are built by combining
# a format with subjects that have NOT appeared recently, so the channel never recycles
# the same matchup or creature (YouTube suppresses repetitive/inauthentic content).
FACTS_CREATURES = [
    "colossal squid", "giant squid", "sperm whale", "megalodon", "mosasaur", "liopleurodon",
    "dunkleosteus", "helicoprion", "ichthyosaur", "elasmosaurus", "kronosaurus", "basilosaurus",
    "livyatan", "anomalocaris", "sea scorpion (eurypterid)", "ammonite", "giant pacific octopus",
    "sleeper shark", "greenland shark", "goblin shark", "frilled shark", "megamouth shark",
    "cookiecutter shark", "bluntnose sixgill shark", "great white shark", "orca", "box jellyfish",
    "blue-ringed octopus", "lion's mane jellyfish", "immortal jellyfish", "giant siphonophore",
    "barreleye fish", "anglerfish", "black swallower", "gulper eel", "fangtooth fish",
    "viperfish", "dragonfish", "giant isopod", "yeti crab", "pompeii worm", "scaly-foot snail",
    "vampire squid", "dumbo octopus", "glass octopus", "mimic octopus", "coconut octopus",
    "giant oarfish", "coelacanth", "hagfish", "lamprey", "mantis shrimp", "pistol shrimp",
    "japanese spider crab", "bobbit worm", "zombie worm (osedax)", "tardigrade", "sea pig",
    "chambered nautilus", "blobfish", "sarcastic fringehead", "stonefish", "lionfish",
    "electric eel", "humboldt squid", "leatherback sea turtle", "narwhal", "beluga whale",
    "cuvier's beaked whale", "leafy seadragon", "pacific viperfish", "telescope octopus",
    "christmas tree worm", "portuguese man o' war", "giant tube worm", "sea angel", "comb jelly",
    "nudibranch", "parrotfish", "moray eel", "saltwater crocodile", "thresher shark",
]

FACTS_PHENOMENA = [
    "underwater brine lakes that pickle animals", "hydrothermal black smoker vents",
    "underwater waterfalls bigger than Niagara", "milky seas glowing for miles",
    "the bloop and other unexplained ocean sounds", "rogue waves taller than buildings",
    "underwater rivers flowing on the seafloor", "brinicles (ice fingers of death)",
    "whale falls feeding entire ecosystems", "the midnight zone where light never reaches",
    "bioluminescent bays", "the Mariana Trench Challenger Deep", "underwater volcanoes erupting",
    "methane ice that burns underwater", "ocean dead zones", "the great Pacific garbage patch",
    "the Antarctic underwater lake Vostok", "underwater forests of giant kelp",
    "Lake Nyos and limnic eruptions", "the ocean's daily vertical migration",
    "submarine landslides and megatsunamis", "underwater crop circles made by pufferfish",
    "red tides and toxic algae blooms", "the Mid-Atlantic Ridge splitting the planet",
    "petrified forests under the sea", "underwater cave systems (cenotes)",
    "the oxygen-producing dark metal nodules", "the snowball earth ice age oceans",
    "the Cambrian explosion", "the great dying mass extinction", "the asteroid that killed the dinosaurs hitting the ocean",
]

# (category, subject kind, template). Categories are weighted by real channel views
# (see performance_tracker.py), so formats that perform better get picked more often.
FACTS_FORMATS = [
    # Duels: highest debate & comment multiplier
    ("duel", "duel", "Ocean Duel: {a} vs {b} (who would win and why? use real biology)"),
    ("duel", "duel", "Size & Power Showdown: {a} vs {b} (compare weapons, size, speed)"),
    # Quizzes: force replays & comments
    ("quiz", "single", "Quiz: 2 real mind-blowing facts and 1 fake lie about the {a} (can you spot the lie?)"),
    ("guess", "single", "Guess the creature: describe the {a} with 3 clues, reveal it at the end"),
    # Deep dives: retention & loop
    ("deep_dive", "single", "The single most bizarre real superpower of the {a}"),
    ("deep_dive", "single", "Why the {a} is scarier (or weirder) than you think"),
    ("deep_dive", "phenomenon", "The terrifying truth about {a}"),
    ("deep_dive", "phenomenon", "What would happen to you inside {a}?"),
]

def classify_title(title):
    """Best-effort format category for titles generated before categories were recorded."""
    t = title.lower()
    if re.search(r"\bvs\.?\b|versus|who wins|who would win|duel|battle|showdown|brawl|clash", t):
        return "duel"
    if re.search(r"\blie\b|fake|quiz|true or false", t):
        return "quiz"
    if "guess" in t:
        return "guess"
    return "deep_dive"

# How many past videos a subject must wait before it can be reused
SUBJECT_COOLDOWN = 80
STOICISM_SUBTOPICS = [
    "how to deal with difficult people", "overcoming fear of failure", "embracing change and mortality",
    "mastering anger and emotions", "finding peace in a chaotic world", "letting go of things you can't control",
    "the power of self-discipline", "turning obstacles into opportunities", "valuing time over possessions",
    "building inner strength and resilience"
]

from config import NICHES, BASE_DIR

# History tracking file to guarantee 0 repetitions
HISTORY_FILE = BASE_DIR / "used_scripts_history.json"

def _repair_history_text(text):
    """Strip git conflict markers (keeping both sides) and restore missing list commas."""
    text = re.sub(r'^(<<<<<<<|=======|>>>>>>>).*\n', '', text, flags=re.M)
    return re.sub(r'"(\s*\n\s*)"', r'",\1"', text)

def load_history():
    if not HISTORY_FILE.exists():
        return {"used_titles": [], "used_fallbacks": {"facts": [], "stoicism": []}}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Never silently fall back to an empty history: that disables the anti-repetition guard
    try:
        history = json.loads(_repair_history_text(text))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{HISTORY_FILE.name} is corrupted and could not be repaired: {e}")
    print(f"[HISTORY] Repaired corrupted {HISTORY_FILE.name} (git conflict markers removed).")
    save_history(history)
    return history

def _recently_used(subject, history):
    """A subject is 'recent' if it was picked or mentioned in a title within the cooldown window."""
    recent_subjects = history.get("used_subjects", [])[-SUBJECT_COOLDOWN:]
    if subject in recent_subjects:
        return True
    # Match on the main name (e.g. "zombie worm (osedax)" -> "zombie worm") against recent titles
    name = subject.split("(")[0].strip().lower()
    recent_titles = " | ".join(history.get("used_titles", [])[-SUBJECT_COOLDOWN:]).lower()
    return name in recent_titles

def pick_fresh_facts_subtopic(history, exclude=()):
    """Builds a subtopic from a random format using only subjects outside the cooldown window.

    Returns:
        tuple: (subtopic_text, [subjects used], format category)
    """
    creatures = [c for c in FACTS_CREATURES if c not in exclude and not _recently_used(c, history)]
    phenomena = [p for p in FACTS_PHENOMENA if p not in exclude and not _recently_used(p, history)]
    # If a pool runs dry, fall back to the least-recently-used half instead of repeating the newest
    if len(creatures) < 2:
        creatures = [c for c in FACTS_CREATURES if c not in history.get("used_subjects", [])[-SUBJECT_COOLDOWN // 2:]]
    if not phenomena:
        phenomena = [p for p in FACTS_PHENOMENA if p not in history.get("used_subjects", [])[-SUBJECT_COOLDOWN // 2:]]

    category_weights = history.get("format_weights", {}).get("weights", {})
    weights = [category_weights.get(f[0], 1.0) for f in FACTS_FORMATS]
    category, kind, template = random.choices(FACTS_FORMATS, weights=weights)[0]
    if kind == "duel":
        subjects = random.sample(creatures, 2)
        return template.format(a=subjects[0], b=subjects[1]), subjects, category
    if kind == "single":
        subjects = [random.choice(creatures)]
    else:
        subjects = [random.choice(phenomena)]
    return template.format(a=subjects[0]), subjects, category

def fetch_reference_facts(subjects, max_chars=1800):
    """Fetches the Wikipedia intro for each subject so the script is grounded in real facts.

    Returns:
        str: "Subject: extract" blocks, or "" if Wikipedia is unreachable.
    """
    import requests
    blocks = []
    for subject in subjects:
        name = subject.split("(")[0].strip()
        try:
            resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "format": "json", "generator": "search", "gsrsearch": name,
                        "gsrlimit": 1, "prop": "extracts", "exintro": 1, "explaintext": 1, "redirects": 1},
                headers={"User-Agent": "NicosaurusShortsBot/1.0 (educational YouTube channel)"},
                timeout=15,
            )
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "").strip()
                if extract:
                    blocks.append(f"{page.get('title', name)}: {extract[:max_chars]}")
        except Exception as e:
            print(f"[FACTS] Could not fetch Wikipedia reference for '{name}': {e}")
    return "\n\n".join(blocks)

def is_too_similar(title, past_titles, threshold=0.72):
    """True when the title is a near-duplicate of any of the last 150 titles."""
    t = re.sub(r'[^a-z0-9 ]', '', title.lower()).strip()
    for past in past_titles[-150:]:
        p = re.sub(r'[^a-z0-9 ]', '', past.lower()).strip()
        if t and difflib.SequenceMatcher(None, t, p).ratio() >= threshold:
            return True
    return False

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save script history: {e}")

def save_and_return_fallback(niche_key, video_dir):
    """Select and return a fallback script that has NOT been used before.
    
    When all fallbacks are exhausted, creates a mashup from two random fallbacks
    to produce a unique-enough script rather than repeating.
    """
    history = load_history()
    used_indices = history.get("used_fallbacks", {}).get(niche_key, [])
    available_indices = [i for i in range(len(FALLBACKS[niche_key])) if i not in used_indices]
    
    if not available_indices:
        # ALL fallbacks used — create a mashup to avoid repetition
        print("All fallback scripts exhausted. Creating unique mashup...")
        pool = FALLBACKS[niche_key]
        a, b = random.sample(range(len(pool)), 2)
        mashup_data = {
            "title": pool[a]["title"].replace("3 ", "NEW ").replace("How ", "Why "),
            "script": pool[a]["script"],  # Use one script
            "keywords": pool[b]["keywords"]  # With different keywords (= different images)
        }
        try:
            script_path = video_dir / f"{niche_key}_script.txt"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(mashup_data["script"])
        except Exception as e:
            print(f"Error saving fallback script to file: {e}")
        return mashup_data
        
    chosen_idx = random.choice(available_indices)
    used_indices.append(chosen_idx)
    if "used_fallbacks" not in history:
        history["used_fallbacks"] = {}
    history["used_fallbacks"][niche_key] = used_indices
    save_history(history)
    
    fallback_data = FALLBACKS[niche_key][chosen_idx]
    try:
        script_path = video_dir / f"{niche_key}_script.txt"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(fallback_data["script"])
    except Exception as e:
        print(f"Error saving fallback script to file: {e}")
    return fallback_data

# Standard Fallback Data (Randomized pool to avoid repetition without API keys)
FALLBACKS = {
    "facts": [
        {
            "title": "3 Mind-Blowing Universe Facts That Sound Fake 🤯",
            "script": "Did you know that the universe is actually much weirder than you think? First, a day on Venus is longer than a year on Venus! Second, honey never spoils. Pots of honey from Egyptian tombs are still edible! Third, astronauts have a Velcro patch inside their helmets to scratch their noses! Subscribe for more mind-blowing facts!",
            "keywords": ["universe galaxy", "planet venus", "space spin", "honey jar", "egyptian tomb", "edible food", "astronaut helmet", "velcro patch", "scratching nose", "mind blowing", "science fact", "outer space", "ancient history", "human body", "wow expression"]
        },
        {
            "title": "3 Psychology Facts That Will Mess With Your Head 🧠",
            "script": "Here are three psychological facts that will mess with your head! One, your brain can't create new faces in dreams, every person you dream of is someone you've seen! Two, if you announce your goals to others, you are less likely to succeed. Three, the average person tells four lies a day. Hit subscribe if you didn't lie today!",
            "keywords": ["human brain", "sleeping face", "dreaming clouds", "goal mountain", "success trophy", "talking mouth", "secret whisper", "lying face", "truth glowing", "psychology head", "mind blown", "mystery shadow", "people crowd", "clock ticking", "wow expression"]
        },
        {
            "title": "Why The Deep Ocean Will Terrify You 🌊",
            "script": "The ocean is terrifying, and here is why. We have explored less than five percent of the deep ocean. There are underwater lakes and rivers at the bottom of the sea that have their own waves! And finally, the largest waterfall on Earth is actually underwater in the Denmark Strait. Subscribe if you love the ocean!",
            "keywords": ["dark ocean", "deep sea", "underwater lake", "ocean waves", "underwater river", "waterfall falling", "denmark map", "sea creature", "scary water", "blue depth", "submarine exploring", "fish swimming", "nature beauty", "water splash", "wow expression"]
        },
        {
            "title": "Unbelievable History Facts You Were Never Taught 🏛️",
            "script": "Did you know that some history facts will sound completely fake? First, Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid! Second, Oxford University is older than the Aztec Empire! Third, the shortest war in history lasted only thirty-eight minutes! Subscribe for more unbelievable facts!",
            "keywords": ["ancient history", "cleopatra queen", "moon landing astronaut", "great pyramid egypt", "oxford university", "ancient library", "aztec empire ruins", "shortest war battle", "clock ticking fast", "surprised person", "mind blowing", "science fact", "ancient history", "human body", "wow expression"]
        },
        {
            "title": "Mysterious Human Body Secrets You Didn't Know 🧬",
            "script": "The human body is way more mysterious than you realize! One, your brain generates enough electricity to power a small lightbulb! Two, humans are the only animals capable of shedding emotional tears! Three, acid in your stomach is strong enough to dissolve razor blades! Subscribe to uncover more bodily secrets!",
            "keywords": ["human body silhouette", "glowing human brain", "electric lightbulb glowing", "crying eye tear", "crying face emotion", "stomach acid glowing", "razor blade melting", "microscopic cells", "medical science", "mind blown", "mystery shadow", "people crowd", "clock ticking", "wow expression", "science fact"]
        },
        {
            "title": "Animals With Actual Real Life Superpowers 🐆",
            "script": "There are animals on Earth that practically have superpowers! First, a tardigrade can survive the vacuum of outer space and extreme temperatures! Second, shrimps have their hearts located inside their heads! Third, a jellyfish called the immortal jellyfish can reverse its aging process and live forever! Hit subscribe for more amazing nature secrets!",
            "keywords": ["nature forest wildlife", "microscopic tardigrade", "outer space starfield", "shrimp swimming underwater", "shrimp anatomy head", "immortal jellyfish glowing", "ocean depths dark", "underwater creature magic", "immortality clock backward", "mind blowing", "science fact", "outer space", "ancient history", "human body", "wow expression"]
        },
        {
            "title": "Terrifying Things Hiding In Outer Space 🌌",
            "script": "Space is hiding things that will terrify you! One, there is a giant cloud of alcohol in outer space that contains enough booze to fill four hundred trillion pints of beer! Two, a day on Venus is longer than a year on Venus, and it rains sulfuric acid! Three, neutron stars spin at up to six hundred times per second! Subscribe for more space secrets!",
            "keywords": ["deep space galaxy", "giant gas cloud alcohol", "pint beer glass", "venus planet glowing", "sulfuric acid rain storm", "neutron star spinning", "cosmic explosion supernova", "telescope space observatory", "scary universe mystery", "blue depth", "submarine exploring", "fish swimming", "nature beauty", "water splash", "wow expression"]
        },
        {
            "title": "How Your Mind Is Playing Tricks On You 💭",
            "script": "Your mind is playing tricks on you right now! First, the Placebo Effect can work even when you know you are taking a sugar pill! Second, we are more creative when we are tired because our brain filters are relaxed! Third, your brain remembers memories by re-saving them, meaning every memory is slightly altered! Subscribe for more psychology secrets!",
            "keywords": ["human mind silhouette", "sugar pill placebo", "creative brain glowing spark", "tired yawning person", "relaxed brain waves", "memory recall brain", "photo album fading", "psychology head", "mind blown", "mystery shadow", "people crowd", "clock ticking", "wow expression", "science fact", "human body"]
        }
    ],
    "stoicism": [
        {
            "title": "How To Turn Any Obstacle Into Power 🏛️",
            "script": "The obstacle in the path becomes the path. Within every obstacle is an opportunity to improve. Marcus Aurelius wrote: 'You have power over your mind, not outside events. Realize this, and you will find strength.' When life throws you into chaos, do not seek to control the storm. Control how you respond to it. Subscribe to build your mental armor.",
            "keywords": ["ancient greek statue", "marcus aurelius philosopher", "storm dark sky", "shield armor", "obstacle path", "opportunity open door", "mind power", "brain glowing", "outside events", "inner strength", "chaos life", "control response", "mental armor", "daily wisdom", "stoic reflection"]
        },
        {
            "title": "Stop Letting Anxiety Destroy Your Peace ⏳",
            "script": "Seneca once said: We suffer more often in imagination than in reality. Why do you let anxiety about the future destroy your peace today? A true stoic understands that tomorrow is not promised, and yesterday is gone. All you have is this exact moment. Breathe. Focus. Subscribe for daily stoic wisdom.",
            "keywords": ["seneca philosopher", "roman empire", "anxiety shadow", "peaceful mind", "time passing clock", "hourglass sand", "breathe in out", "meditation calm", "focus target", "stoic man", "ancient Rome", "sun setting", "mindful moment", "strong mind", "stoic reflection"]
        },
        {
            "title": "How To Stop Letting People Control Your Emotions 🛡️",
            "script": "If you are distressed by anything external, the pain is not due to the thing itself, but to your estimate of it. You can wipe this out at any moment. You are the architect of your own mood. Stop giving people the remote control to your emotions. Master yourself. Subscribe to take control of your life.",
            "keywords": ["architect blueprints", "mood swinging", "remote control", "puppet strings", "mastering self", "strong chains", "breaking free", "greek pillar", "stoic bust", "calm ocean", "storm clearing", "focus eye", "mental strength", "wisdom book", "stoic reflection"]
        },
        {
            "title": "The Secret To Absolute Mental Freedom 🦅",
            "script": "The secret to absolute freedom is wanting nothing. Epictetus taught that we should not seek to have events happen as we want, but wish them to happen as they do. True wealth is not having many possessions, but having few wants. By desiring less, you take away the power of others to control or disappoint you. Subscribe for daily discipline.",
            "keywords": ["ancient greek statue", "epictetus philosopher", "wealthy gold coins", "simple living minimal", "free man standing cliff", "control response", "mental armor", "daily wisdom", "stoic reflection", "peaceful mind", "meditation calm", "focus target", "stoic man", "ancient Rome", "sun setting"]
        },
        {
            "title": "A Stoic Rule To Stop Overthinking Today 🧘",
            "script": "You are destroying your own peace by overthinking. Marcus Aurelius said: 'Very little is needed to make a happy life; it is all within yourself, in your way of thinking.' Stop projecting future pain that has not happened yet. The present moment is the only place where life exists. Lock your mind to it. Subscribe to protect your peace.",
            "keywords": ["anxiety shadow overthinking", "marcus aurelius philosopher", "happy life joy peace", "inner self mind glowing", "future pain dark storm", "present moment focus", "lock keys safety", "calm serene landscape", "architect blueprints", "mood swinging", "remote control", "puppet strings", "mastering self", "strong chains", "breaking free"]
        },
        {
            "title": "Why Silence Is Your Most Powerful Weapon 🤐",
            "script": "To master your life, you must first master your tongue. Zeno of Citium, the founder of Stoicism, said: 'We have two ears and one mouth, so we should listen more than we speak.' Speaking without thinking is like shooting without aiming. Silence is often the most powerful response to insult. Let your calm speak for you. Subscribe for daily strength.",
            "keywords": ["zeno of citium statue", "glowing ears listening", "mouth speaking silent", "arrow shooting target", "silence calm peaceful", "calm ocean water", "stoic philosopher reflection", "ancient greek statue", "mind power", "brain glowing", "outside events", "inner strength", "chaos life", "control response", "mental armor"]
        },
        {
            "title": "How To Build Unshakeable Mental Toughness ⚔️",
            "script": "Hard times are not your enemy, they are your training ground. Seneca wrote: 'Fire is the test of gold; adversity, of strong men.' Comfort makes you weak and unprepared for life's inevitable storms. Embrace discomfort deliberately to build a mind that cannot be broken. Subscribe to harden your spirit.",
            "keywords": ["stormy weather sea waves", "gold fire smelting", "comfort zone cozy bed", "strong warrior armor", "deliberate hardship training", "iron breaking chains", "stoic bust stone", "architect blueprints", "mood swinging", "remote control", "puppet strings", "mastering self", "strong chains", "breaking free", "greek pillar"]
        },
        {
            "title": "The Harsh Truth About Time You Need To Hear ⏰",
            "script": "Death is not in the future, it is happening right now. Seneca reminded us that the time that has passed belongs to death. Memento Mori. Remember that you are mortal. Let this truth clarify what truly matters. Stop wasting your life on trivial arguments and petty desires. Live deeply today. Subscribe to wake up.",
            "keywords": ["hourglass sand running out", "memento mori skull", "death shadow silhouette", "clarity vision focus", "trivial drama arguments", "living deeply nature meditation", "stoic philosopher reflection", "ancient Rome", "sun setting", "mindful moment", "strong mind", "stoic reflection", "time passing clock", "hourglass sand", "breathe in out"]
        }
    ]
}

def clean_json_response(raw_text):
    """Extract a JSON object from the raw Gemini response.
    
    Handles the common Gemini issue where real newlines appear inside JSON
    string values (which is invalid JSON). Fixes this by replacing literal
    newlines within quoted strings with spaces.
    """
    cleaned = raw_text.strip()
    
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        first_nl = cleaned.find("\n")
        if first_nl != -1:
            cleaned = cleaned[first_nl+1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    
    # Extract from first { to last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return cleaned
    
    json_str = cleaned[start:end+1]
    
    # CRITICAL FIX: Gemini often outputs \' (escaped single quotes) which is
    # invalid JSON. Replace \' with just ' before parsing.
    json_str = json_str.replace("\\'", "'")
    
    # Fix real newlines inside JSON string values by walking through the string
    # and replacing \n with space when we're inside a quoted value
    result = []
    in_string = False
    i = 0
    while i < len(json_str):
        ch = json_str[i]
        if ch == '"' and (i == 0 or json_str[i-1] != '\\'):
            in_string = not in_string
            result.append(ch)
        elif in_string and ch in ('\n', '\r'):
            result.append(' ')  # Replace newline inside string with space
        else:
            result.append(ch)
        i += 1
    
    return ''.join(result)

def _extract_fields_regex(raw_text):
    """Bulletproof regex extraction of title, script, and keywords from raw Gemini text.
    
    Handles multiline strings by first normalizing newlines inside the text.
    """
    # Normalize: replace real newlines with spaces, fix escaped single quotes
    normalized = raw_text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\\'", "'")
    
    title = ""
    script = ""
    keywords = []
    
    # Title
    t = re.search(r'"title"\s*:\s*"([^"]+)"', normalized)
    if t:
        title = t.group(1)
    
    # Script: find "script": "..." with the content potentially very long
    s_match = re.search(r'"script"\s*:\s*"', normalized)
    if s_match:
        start_pos = s_match.end()
        # Walk forward looking for the closing quote (not preceded by backslash)
        i = start_pos
        while i < len(normalized):
            if normalized[i] == '"' and normalized[i-1] != '\\':
                script = normalized[start_pos:i]
                break
            i += 1
        # Clean escaped characters
        script = script.replace('\\"', '"').replace('\\n', ' ').replace('\\r', ' ')
    
    # Keywords
    k = re.search(r'"keywords"\s*:\s*\[(.*?)\]', normalized, re.DOTALL)
    if k:
        kw_raw = k.group(1)
        keywords = [w.strip().strip('"').strip("'") for w in kw_raw.split(",")]
        keywords = [w for w in keywords if w and len(w) > 1]
    
    print(f"[REGEX DEBUG] Extracted Title len: {len(title)}")
    print(f"[REGEX DEBUG] Extracted Script len: {len(script)}")
    print(f"[REGEX DEBUG] Extracted Keywords: {len(keywords)}")
    if len(script) <= 30:
        print(f"[REGEX DEBUG] Normalized string (first 1000 chars):\n{normalized[:1000]}")
    
    return title, script, keywords

# Valid reaction types that map to pre-generated PNG files in assets/reactions/
VALID_REACTIONS = ["shocked", "scared", "thinking", "excited", "mindblown", "curious", "crying", "waving"]

def _call_gemini(prompt, temperature=0.9, extra_parts=None, json_mode=False, timeout=30):
    """Calls Gemini with a model fallback chain and returns the raw response text.

    extra_parts: additional content parts placed before the prompt (e.g. an uploaded video file).
    """
    import requests
    import time
    api_key = os.environ.get("GEMINI_API_KEY", "")
    models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-3.5-flash"]
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    payload = {
        "contents": [{"parts": (extra_parts or []) + [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192
        }
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    resp = None
    for model_name in models_to_try:
        # API key goes in a header, never in the URL, so it cannot leak into error messages/CI logs
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    break
                elif resp.status_code in (429, 503, 500, 502, 504):
                    print(f"Model {model_name} returned status {resp.status_code}. Retrying...")
                    time.sleep(2)
            except Exception as ex:
                print(f"Connection error with {model_name}: {ex}")
                time.sleep(2)
        if resp is not None and resp.status_code == 200:
            print(f"Gemini responded using {model_name}.")
            break

    if resp is None or resp.status_code != 200:
        if resp is not None:
            resp.raise_for_status()
        raise RuntimeError("All Gemini models failed to respond.")

    return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()

def _parse_response(raw_text, niche_key):
    """Parses a Gemini response into (title, script, scenes, keywords), or None if unusable."""
    cleaned_text = clean_json_response(raw_text)

    # Attempt 1: Direct JSON parse
    data = None
    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Remove control characters and retry
    if not data:
        try:
            sanitized = re.sub(r'[\x00-\x1F\x7F]', ' ', cleaned_text)
            data = json.loads(sanitized)
        except json.JSONDecodeError:
            pass

    # Attempt 3: Regex field extraction (handles multiline strings, escaped quotes, etc.)
    if not data or not isinstance(data, dict):
        print("Extracting script fields via regex parser...")
        title, script, keywords = _extract_fields_regex(raw_text)
        if script and len(script) > 30:
            data = {"title": title, "script": script, "keywords": keywords}
        else:
            print(f"REGEX FAILED. Raw response was:\n{raw_text[:800]}\n...")

    if not (data and isinstance(data.get("script"), str) and len(data["script"].strip()) > 30):
        return None

    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        scenes = []

    # If no scenes are present but keywords are (like for Stoicism or regex fallbacks)
    if not scenes:
        keywords = data.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        # Map keywords to scenes
        for idx, kw in enumerate(keywords):
            reaction = VALID_REACTIONS[idx % len(VALID_REACTIONS)] if niche_key == "facts" else ""
            scenes.append({"keyword": kw, "reaction": reaction})
    else:
        # Ensure each scene object is properly formatted
        for idx, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                scenes[idx] = {"keyword": str(scene), "reaction": ""}
            if "keyword" not in scenes[idx]:
                scenes[idx]["keyword"] = ""
            reaction_val = scenes[idx].get("reaction", "").strip().lower()
            # Validate reaction is one of our pre-made types
            if reaction_val not in VALID_REACTIONS:
                # Try to infer the closest valid reaction from freeform text
                inferred = VALID_REACTIONS[idx % len(VALID_REACTIONS)]
                for vr in VALID_REACTIONS:
                    if vr in reaction_val:
                        inferred = vr
                        break
                scenes[idx]["reaction"] = inferred
            else:
                scenes[idx]["reaction"] = reaction_val

    # Enforce scene count limit
    target_kw_count = 7 if niche_key == "facts" else 15
    if len(scenes) < target_kw_count:
        # Add default scenes if count is too low
        fallback_scenes = [
            {"keyword": "mind blowing universe", "reaction": "looking completely mindblown"},
            {"keyword": "curious science details", "reaction": "inspecting with a magnifying glass"}
        ]
        for i in range(target_kw_count - len(scenes)):
            fs = fallback_scenes[i % len(fallback_scenes)]
            reaction = VALID_REACTIONS[len(scenes) % len(VALID_REACTIONS)] if niche_key == "facts" else ""
            scenes.append({"keyword": fs["keyword"], "reaction": reaction})
    elif len(scenes) > target_kw_count:
        scenes = scenes[:target_kw_count]

    # Generate keywords list for compatibility with other parts of the pipeline
    keywords = [s["keyword"].strip() for s in scenes if s.get("keyword")]

    title = str(data.get("title", "")).strip().replace('\\"', '"').replace('\n', ' ')
    if not title:
        title = f"Mind-Blowing {niche_key.capitalize()} You Need To Know 🤯" if niche_key == "facts" else "Stoic Rule To Master Your Life 🏛️"

    script_content = str(data["script"]).strip().replace('\\"', '"').replace('\n', ' ')
    return title, script_content, scenes, keywords

def generate_script(niche_key, video_dir, topic=None):
    """Generates a structured video script, viral title, and keywords/scenes using Gemini API.

    Subjects rotate through large pools with a cooldown, and near-duplicate titles are
    regenerated, so the channel does not publish repetitive content.

    Returns:
        dict: {"title": str, "script": str, "scenes": list, "keywords": list}
    """
    if niche_key not in NICHES:
        raise ValueError(f"Niche '{niche_key}' is not configured.")

    niche = NICHES[niche_key]
    history = load_history()
    used_titles = history.get("used_titles", [])
    used_scripts = history.get("used_scripts", [])

    print(f"Generating script, viral title and keywords/scenes for niche '{niche['name']}' using Gemini...")

    # Check if API key is configured
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "sua_chave_do_gemini_aqui":
        print("\n[!] CRITICAL ERROR: No valid GEMINI_API_KEY found.")
        print("[!] The pipeline will now abort to guarantee zero duplicate videos.")
        return None

    import ai_reviewer

    rejected_subjects = []
    retry_with = None  # (subtopic, subjects, category, critique) when a draft is rejected on quality
    rejections_on_topic = 0
    reference_cache = {}
    max_attempts = 3
    try:
        for attempt in range(max_attempts):
            prompt = niche["prompt_template"]
            subjects = []
            category = None
            reference = ""
            if topic:
                prompt += f"\n\nSpecifically, the video should be about this topic/theme: '{topic}'."
            else:
                if retry_with:
                    subtopic, subjects, category, _ = retry_with
                elif niche_key == "facts":
                    subtopic, subjects, category = pick_fresh_facts_subtopic(history, exclude=rejected_subjects)
                else:
                    subtopic = random.choice(STOICISM_SUBTOPICS)
                print(f"[TOPIC] {subtopic}")

                # Ground the script in real sources: Gemini invents facts about obscure animals otherwise
                if subjects:
                    key = tuple(subjects)
                    if key not in reference_cache:
                        reference_cache[key] = fetch_reference_facts(subjects)
                    reference = reference_cache[key]
                if reference:
                    prompt += ("\n\nREFERENCE FACTS (from Wikipedia). Every factual claim in the script MUST be supported by "
                               "these references. Do not attribute behaviors of related species to this one. Do not invent "
                               f"numbers.\n{reference}")

                # Inject past titles AND past script summaries to avoid repeats
                past_titles_str = ", ".join(used_titles[-40:]) if used_titles else "None"
                past_scripts_summary = "; ".join([s[:60] for s in used_scripts[-10:]]) if used_scripts else "None"
                prompt += f"\n\nFocus specifically on this sub-category: '{subtopic}'."
                prompt += f"\n\nCRITICAL: You MUST generate a completely NEW and UNIQUE script. DO NOT repeat or reuse ideas, title structures or wording from these past titles: [{past_titles_str}]."
                prompt += f"\nAlso avoid these past script openings: [{past_scripts_summary}]."

            # Learn from what actually got views on the channel (style only, never the topics)
            top_titles = history.get("format_weights", {}).get("top_titles", [])
            if top_titles:
                prompt += f"\n\nThese past titles got the MOST views on this channel. Match their energy and title style, but NOT their topics: [{', '.join(top_titles)}]."
            if retry_with:
                prompt += f"\n\nA previous draft on this topic was REJECTED by the editor for these reasons, fix them: {retry_with[3]}"

            temperature = 0.9 + 0.15 * attempt
            parsed = _parse_response(_call_gemini(prompt, temperature), niche_key)
            if not parsed:
                print(f"[!] Gemini response could not be parsed (attempt {attempt + 1}/{max_attempts}).")
                continue

            title, script_content, scenes, keywords = parsed
            script_start = script_content[:50].lower()
            duplicate_opening = any(script_start == past[:50].lower() for past in used_scripts)
            if (duplicate_opening or is_too_similar(title, used_titles)) and attempt < max_attempts - 1:
                print(f"WARNING: '{title}' is too similar to a past video. Regenerating with a new topic...")
                rejected_subjects.extend(subjects)
                retry_with = None
                continue

            # Editorial review before spending minutes on rendering
            review = ai_reviewer.review_script(title, script_content, scenes, reference)
            if review and not review["passed"]:
                if attempt < max_attempts - 1:
                    rejections_on_topic += 1
                    if topic or rejections_on_topic >= 2:
                        # Same topic failed twice: the subject is too obscure, try another one
                        print("WARNING: Script rejected again. Switching to a new topic...")
                        rejected_subjects.extend(subjects)
                        retry_with = None
                        rejections_on_topic = 0
                    else:
                        print("WARNING: Script rejected by AI editor. Rewriting with its feedback...")
                        retry_with = (subtopic, subjects, category, "; ".join(review["issues"]))
                    continue
                if review["scores"]["facts"] < ai_reviewer.MIN_FACT_SCORE:
                    # Never publish a script the editor flagged as factually wrong
                    print("\n[!] All drafts had factual errors. No script approved for this round.")
                    if subjects:
                        history["used_subjects"] = history.get("used_subjects", []) + subjects
                        save_history(history)
                    return None
            break
        else:
            print("\n[!] CRITICAL ERROR: Gemini response could not be parsed.")
            print("[!] The pipeline will now abort to guarantee zero duplicate videos.")
            return None

        # Save to history
        used_titles.append(title)
        used_scripts.append(script_content)
        history["used_titles"] = used_titles
        history["used_scripts"] = used_scripts
        if subjects:
            history["used_subjects"] = history.get("used_subjects", []) + subjects
        if category:
            history.setdefault("title_formats", {})[title] = category
        save_history(history)

        result = {
            "title": title,
            "script": script_content,
            "scenes": scenes,
            "keywords": [k.strip() for k in keywords]
        }

        # Save script text to file
        script_path = video_dir / f"{niche_key}_script.txt"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(result["script"])

        print(f"Generated Live Title: '{result['title']}'")
        print("Script and keywords generated successfully via Gemini API!")
        return result

    except Exception as e:
        print(f"\n[!] CRITICAL ERROR: Gemini API failed after multiple retries.")
        print(f"[!] Reason: {e}")
        print("[!] The pipeline will now abort to guarantee zero duplicate videos.")
        return None
