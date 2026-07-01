import os
import json
import re
import random
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from dotenv import load_dotenv
from config import NICHES

# Load environment variables
load_dotenv()

# Initialize Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "sua_chave_do_gemini_aqui":
    genai.configure(api_key=api_key)
else:
    print("WARNING: GEMINI_API_KEY not found or is default placeholder in environment. Please add it to your .env file.")

# Sub-topics/angles list to ensure variety in prompts
FACTS_SUBTOPICS = [
    "deep ocean terrifying secrets", "unknown outer space mysteries", 
    "bizarre and scary nature phenomena", "unexplored regions of earth", 
    "terrifying astrophysics facts", "mysterious underwater creatures",
    "the dark universe and black holes", "unexplained archaeological discoveries"
]
STOICISM_SUBTOPICS = [
    "how to deal with difficult people", "overcoming fear of failure", "embracing change and mortality",
    "mastering anger and emotions", "finding peace in a chaotic world", "letting go of things you can't control",
    "the power of self-discipline", "turning obstacles into opportunities", "valuing time over possessions",
    "building inner strength and resilience"
]

from config import NICHES, BASE_DIR

# History tracking file to guarantee 0 repetitions
HISTORY_FILE = BASE_DIR / "used_scripts_history.json"

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"used_titles": [], "used_fallbacks": {"facts": [], "stoicism": []}}

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

def generate_script(niche_key, video_dir, topic=None):
    """Generates a structured video script, viral title, and keywords using Gemini API.
    
    Every generated script is saved to history to guarantee zero repetition.
    
    Returns:
        dict: {"title": str, "script": str, "keywords": list}
    """
    if niche_key not in NICHES:
        raise ValueError(f"Niche '{niche_key}' is not configured.")
        
    niche = NICHES[niche_key]
    prompt = niche["prompt_template"]
    
    history = load_history()
    used_titles = history.get("used_titles", [])
    used_scripts = history.get("used_scripts", [])
    
    if topic:
        prompt += f"\n\nSpecifically, the video should be about this topic/theme: '{topic}'."
    else:
        if niche_key == "facts":
            subtopic = random.choice(FACTS_SUBTOPICS)
        else:
            subtopic = random.choice(STOICISM_SUBTOPICS)
        
        # Inject past titles AND past script summaries to guarantee zero repeats
        past_titles_str = ", ".join(used_titles[-20:]) if used_titles else "None"
        past_scripts_summary = "; ".join([s[:60] for s in used_scripts[-10:]]) if used_scripts else "None"
        prompt += f"\n\nFocus specifically on this sub-category: '{subtopic}'."
        prompt += f"\n\nCRITICAL: You MUST generate a completely NEW and UNIQUE script. DO NOT repeat or reuse ideas from these past titles: [{past_titles_str}]."
        prompt += f"\nAlso avoid these past script openings: [{past_scripts_summary}]."
        try:
            dir_suffix = int(os.path.basename(str(video_dir)).split('_')[-1])
        except (ValueError, IndexError):
            dir_suffix = random.randint(0, 99999)
        prompt += f"\n(UniqueID: {random.randint(100000, 999999)}-{dir_suffix})"
        
    print(f"Generating script, viral title and keywords for niche '{niche['name']}' using Gemini...")
    
    # Check if API key is configured
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "sua_chave_do_gemini_aqui":
        print("\n[!] CRITICAL ERROR: No valid GEMINI_API_KEY found.")
        print("[!] The pipeline will now abort to guarantee zero duplicate videos.")
        return None

    try:
        import requests
        import time
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 8192
            }
        }
        
        max_retries = 3
        resp = None
        for attempt in range(max_retries):
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                break
            elif resp.status_code in (429, 503, 500, 502, 504):
                print(f"API Error {resp.status_code}. Retrying in 15 seconds (Attempt {attempt+1}/{max_retries})...")
                time.sleep(15)
            else:
                resp.raise_for_status()
                
        resp.raise_for_status()
        
        resp_data = resp.json()
        raw_text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()
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
        
        # Validate and package
        if data and isinstance(data.get("script"), str) and len(data["script"].strip()) > 30:
            keywords = data.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = []
                
            target_kw_count = 10 if niche_key == "facts" else 15
            if len(keywords) < target_kw_count:
                fallback_kws = random.choice(FALLBACKS[niche_key])["keywords"]
                keywords += fallback_kws[len(keywords):target_kw_count]
            elif len(keywords) > target_kw_count:
                keywords = keywords[:target_kw_count]
                
            title = str(data.get("title", "")).strip().replace('\\"', '"').replace('\n', ' ')
            if not title:
                title = f"Mind-Blowing {niche_key.capitalize()} You Need To Know 🤯" if niche_key == "facts" else "Stoic Rule To Master Your Life 🏛️"
            
            script_content = str(data["script"]).strip().replace('\\"', '"').replace('\n', ' ')
            
            # Check if this script is too similar to a past one (first 50 chars match)
            script_start = script_content[:50].lower()
            if any(script_start == past[:50].lower() for past in used_scripts):
                print("WARNING: Gemini generated a near-duplicate script! Retrying with higher temperature...")
                
                payload2 = {
                    "contents": [{"parts": [{"text": prompt + "\n\nIMPORTANT: Generate a COMPLETELY DIFFERENT script from anything before. Be creative and surprising!"}]}],
                    "generationConfig": {
                        "temperature": 1.2,
                        "maxOutputTokens": 8192
                    }
                }
                
                resp2 = None
                for attempt in range(max_retries):
                    resp2 = requests.post(url, headers=headers, json=payload2)
                    if resp2.status_code == 200:
                        break
                    elif resp2.status_code in (429, 503, 500, 502, 504):
                        print(f"API Error {resp2.status_code} during uniqueness retry. Waiting 15s (Attempt {attempt+1}/{max_retries})...")
                        time.sleep(15)
                    else:
                        resp2.raise_for_status()
                        
                resp2.raise_for_status()
                
                raw2 = resp2.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                t2, s2, k2 = _extract_fields_regex(raw2)
                if s2 and len(s2) > 30:
                    title = t2 if t2 else title
                    script_content = s2
                    if k2 and len(k2) >= 5:
                        keywords = k2[:15]
            
            # Save to history
            used_titles.append(title)
            used_scripts.append(script_content)
            history["used_titles"] = used_titles
            history["used_scripts"] = used_scripts
            save_history(history)
            
            result = {
                "title": title,
                "script": script_content,
                "keywords": [k.strip() for k in keywords]
            }
            
            # Save script text to file
            script_path = video_dir / f"{niche_key}_script.txt"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(result["script"])
                
            print(f"Generated Live Title: '{result['title']}'")
            print("Script and keywords generated successfully via Gemini API!")
            return result
            
        print("\n[!] CRITICAL ERROR: Gemini response could not be parsed.")
        print("[!] The pipeline will now abort to guarantee zero duplicate videos.")
        return None
        
    except Exception as e:
        print(f"\n[!] CRITICAL ERROR: Gemini API failed after multiple retries.")
        print(f"[!] Reason: {e}")
        print("[!] The pipeline will now abort to guarantee zero duplicate videos.")
        return None


