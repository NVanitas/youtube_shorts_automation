import os
import random
import requests
import re
from pathlib import Path
from tqdm import tqdm
from config import BACKGROUNDS_DIR, MUSIC_DIR

def download_file_with_progress(url, dest_path, desc="Downloading"):
    """Downloads a file showing a progress bar in the CLI."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    response = requests.get(url, stream=True, headers=headers)
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024  # 1 Kibibyte
    
    t = tqdm(total=total_size, unit="iB", unit_scale=True, desc=desc)
    with open(dest_path, "wb") as f:
        for data in response.iter_content(block_size):
            t.update(len(data))
            f.write(data)
    t.close()
    return dest_path

# Lists of Giphy URLs for randomized pattern interrupts and stock videos (using direct i.giphy.com links)
STOCK_GIFS = [
    "https://i.giphy.com/l0IylOPIQSuR5lspu.gif",  # Cyber space travel
    "https://i.giphy.com/l41lFw057l4cLwgRa.gif",  # Digital grid cyber space
    "https://i.giphy.com/3o7qE1YN7aBOFPRw8E.gif",  # Relaxing dark ocean waves
    "https://i.giphy.com/3o7qE4op19fEdQQISc.gif",  # Neon tunnel abstract loop
    "https://i.giphy.com/13FrpeVHbRCQ0.gif",      # Retro starfield hyperspace
    "https://i.giphy.com/xT9IgzoKnwFNmISR8I.gif"   # Colorful speed of light warp
]

MEME_GIFS = [
    "https://i.giphy.com/26ufdipQqU2lhNA4g.gif",  # Classic Mind Blown
    "https://i.giphy.com/l3q2K1wp6Y1uR838k.gif",  # Surprised/impressed face
    "https://i.giphy.com/5GoVllw6q9F2E.gif",      # Shocked kid computer
    "https://i.giphy.com/ebPX2nRe1N0ys.gif",      # Clapping reaction Drake
    "https://i.giphy.com/3ornk57KwDXf81rjWM.gif",  # Obi Wan "Wait, what?"
    "https://i.giphy.com/xT0xeJpD8e4DYnCHq8.gif"   # Surprised dramatic cat
]

def download_ai_image(keyword, dest_path):
    """Generates and downloads a high-quality vertical AI image matching a keyword using Pollinations AI.
    
    Every call uses a unique random seed to guarantee a different image, even for the same keyword.
    """
    import time
    search_tag = requests.utils.quote(keyword.strip())
    
    # Unique seed per call: modulo 4294967290 to prevent 32-bit unsigned integer overflow (which causes Pollinations 500 errors)
    unique_seed = (int(time.time() * 1000) + random.randint(100000, 99999999)) % 4294967290
    
    urls_to_try = [
        f"https://image.pollinations.ai/prompt/{search_tag}%20cinematic%20vertical%20hd?width=1080&height=1920&nologo=true&model=flux&seed={unique_seed}",
        f"https://image.pollinations.ai/prompt/{search_tag}?width=1080&height=1920&nologo=true&seed={unique_seed + 1}",
        f"https://image.pollinations.ai/prompt/{search_tag}?width=1080&height=1920&nologo=true&seed={unique_seed + 2}",
        f"https://image.pollinations.ai/prompt/{search_tag}?width=1080&height=1920&seed={unique_seed + 3}"
    ]
    
    print(f"Generating AI image for keyword '{keyword}'...")
    for idx, url in enumerate(urls_to_try):
        try:
            download_file_with_progress(url, dest_path, desc=f"AI Image ({keyword[:15]})")
            return dest_path
        except Exception as e:
            print(f"AI generation attempt {idx+1} failed for '{keyword}': {e}")
            
    # Fallback to high-quality stock placeholder service if Pollinations is completely unreachable
    fallback_urls = [
        f"https://picsum.photos/1080/1920"
    ]
    for url in fallback_urls:
        try:
            print(f"Trying fallback stock image service for '{keyword}'...")
            download_file_with_progress(url, dest_path, desc=f"Stock Image ({keyword[:15]})")
            return dest_path
        except Exception as e:
            pass
            
    return None

HTTP_HEADERS = {"User-Agent": "NicosaurusShortsBot/1.0 (educational YouTube channel)"}


def fit_vertical(image_path):
    """Turns any image into a 1080x1920 frame: the whole image fitted in the middle over a blurred,
    darkened copy of itself, so landscape photos never get the animal cropped out."""
    from PIL import Image, ImageFilter, ImageEnhance
    with Image.open(image_path) as src:
        img = src.convert("RGB")
    w, h = img.size
    if abs(w / h - 9 / 16) < 0.02:
        img.resize((1080, 1920), Image.Resampling.LANCZOS).save(image_path, "JPEG", quality=92)
        return image_path

    # Blurred background: cover-crop to 9:16
    scale = max(1080 / w, 1920 / h)
    bg = img.resize((int(w * scale) + 1, int(h * scale) + 1), Image.Resampling.LANCZOS)
    left, top = (bg.width - 1080) // 2, (bg.height - 1920) // 2
    bg = bg.crop((left, top, left + 1080, top + 1920)).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)

    # Foreground: fit inside, slightly larger than full width so it fills more of the frame
    fg_scale = min(1180 / w, 1500 / h)
    fg = img.resize((int(w * fg_scale), int(h * fg_scale)), Image.Resampling.LANCZOS)
    bg.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
    bg.save(image_path, "JPEG", quality=92)
    return image_path


_GENERIC_WORDS = {"close", "deep", "dramatic", "cinematic", "underwater", "ocean", "under", "with", "from",
                  "into", "giant", "huge", "attack", "swimming", "view", "footage", "real", "life"}


_NON_PHOTO_WORDS = ("map", "diagram", "distribution", "range", "drawing", "illustration", "label", "logo",
                    "location", "chart", "figure", "fig.", "graph", "plot", "schem", "sketch", "plate", "stamp")


def download_wikimedia_image(query, dest_path, must_match=None):
    """Finds a real photo on Wikimedia Commons (free, no API key).

    must_match: if given, ALL of these words must appear in the file name (used for named species).
    """
    # Otherwise the file name must mention a meaningful word of the query
    tokens = [t for t in re.findall(r"[a-z]+", query.lower()) if len(t) > 3 and t not in _GENERIC_WORDS]
    required = [t for t in re.findall(r"[a-z]+", (must_match or "").lower()) if len(t) > 2]
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "format": "json", "generator": "search",
                    "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": 12,
                    "prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 960},
            headers=HTTP_HEADERS, timeout=20,
        )
        pages = resp.json().get("query", {}).get("pages", {})
        candidates = []
        for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
            info = (page.get("imageinfo") or [{}])[0]
            title = page.get("title", "").lower()
            if info.get("mime") not in ("image/jpeg", "image/png") or info.get("width", 0) < 700:
                continue
            # Skip maps, diagrams, drawings and specimen labels
            if any(w in title for w in _NON_PHOTO_WORDS):
                continue
            if required and not all(t in title for t in required):
                continue
            if not required and tokens and not any(t in title for t in tokens):
                continue
            candidates.append(info.get("thumburl") or info.get("url"))
        if not candidates:
            print(f"No Wikimedia photo found for '{query}'")
            return None
        from media_pool import _download
        _download(random.choice(candidates[:3]), dest_path, max_mb=25)
        return fit_vertical(dest_path)
    except Exception as e:
        print(f"Wikimedia search failed for '{query}': {e}")
        return None


def download_pexels_photo(query, dest_path, api_key):
    """Searches and downloads a portrait photo from Pexels."""
    try:
        resp = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": api_key},
                            params={"query": query, "per_page": 5, "orientation": "portrait"}, timeout=20)
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        url = random.choice(photos)["src"].get("portrait") or photos[0]["src"]["original"]
        download_file_with_progress(url, dest_path, desc=f"Pexels photo ({query[:15]})")
        return fit_vertical(dest_path)
    except Exception as e:
        print(f"Failed to download photo from Pexels for '{query}': {e}")
        return None


def _named_species(keyword):
    """Returns the creature name if the keyword mentions a specific species (stock video sites rarely have those)."""
    from script_generator import FACTS_CREATURES
    kw = keyword.lower()
    for creature in FACTS_CREATURES:
        name = creature.split("(")[0].strip()
        if name in kw:
            return name
    return None


def download_pexels_video(query, dest_path, api_key, used=None):
    """Searches and downloads a vertical video from Pexels API matching the query.

    used: optional set of "pexels:<id>" keys already in this video; those clips are skipped.
    """
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": 15,
        "orientation": "portrait"
    }
    
    try:
        response = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        videos = [v for v in data.get("videos", []) if used is None or f"pexels:{v['id']}" not in used]
        if not videos:
            print(f"No (unused) videos found on Pexels for query '{query}'")
            return None
            
        # Pick among the most relevant results
        video_data = random.choice(videos[:5])
        video_files = video_data.get("video_files", [])
        
        # Filter for vertical HD
        selected_file = None
        for vf in video_files:
            if vf.get("width") == 1080 and vf.get("height") == 1920:
                selected_file = vf
                break
        
        if not selected_file:
            # Fallback to the largest resolution
            selected_file = max(video_files, key=lambda f: f.get("width", 0) * f.get("height", 0))
            
        video_url = selected_file.get("link")
        download_file_with_progress(video_url, dest_path, desc=f"Video ({query[:15]})")
        if used is not None:
            used.add(f"pexels:{video_data['id']}")
        return dest_path
    except Exception as e:
        print(f"Failed to download video from Pexels for '{query}': {e}")
        return None

def _valid_image(path):
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False

def _animal_group(species):
    """'cookiecutter shark' -> 'shark': a generic term stock sites actually have footage for."""
    for group in ("jellyfish", "octopus", "squid", "shark", "whale", "crab", "shrimp", "eel", "worm", "turtle",
                  "fish", "crocodile", "narwhal", "orca", "nautilus", "snail"):
        if group in species:
            return group
    return "deep sea creature"

def prepare_background_assets(niche_key, scenes, video_dir, media=None):
    """Downloads or prepares background assets matching the script scenes.
    
    Named species (e.g. "yeti crab") get real footage/photos of exactly that animal from a
    per-video Wikipedia/Wikimedia pool (videos first); generic scenes get Pexels stock video.
    No media file is used twice in the same video. All sources are free.
    
    media: a media_pool.MediaPool shared across calls for the same video (pass it again when
           replacing scenes so replacements are also distinct).
    
    Returns:
        list of Path: List of paths to the downloaded media assets
    """
    from media_pool import MediaPool
    pexels_key = os.getenv("PEXELS_API_KEY")
    assets = []
    
    assets_dir = video_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if media is None:
        media = MediaPool(video_dir / "media_cache")
    used = media.used_urls
            
    print(f"\nPreparing background assets for {len(scenes)} scenes:")
    for idx, scene in enumerate(scenes):
        kw = scene["keyword"]
        stem = assets_dir / f"bg_asset_{idx}_{len(used)}"
        video_dest = Path(f"{stem}.mp4")
        image_dest = Path(f"{stem}.jpg")
        species = _named_species(kw)

        sources = []
        if species:
            sources.append(lambda: media.next_asset(species, stem))
            if pexels_key:
                sources.append(lambda: download_pexels_video(f"{_animal_group(species)} underwater", video_dest, pexels_key, used))
        elif pexels_key:
            sources.append(lambda: download_pexels_video(kw, video_dest, pexels_key, used))
            sources.append(lambda: download_pexels_photo(kw, image_dest, pexels_key))
        if not species:
            sources.append(lambda: download_wikimedia_image(kw, image_dest))
        # Last resorts: on-niche generic footage/photos, then any HD photo
        if pexels_key:
            sources.append(lambda: download_pexels_video("deep ocean underwater", video_dest, pexels_key, used))
        if species:
            sources.append(lambda: download_wikimedia_image(_animal_group(species), image_dest))
        generic = random.choice(["underwater ocean", "coral reef underwater", "ocean underwater light", "underwater diver"])
        sources.append(lambda: download_wikimedia_image(generic, image_dest))
        sources.append(lambda: download_file_with_progress(f"https://picsum.photos/seed/{idx+100}/1080/1920", image_dest, desc=f"HD Stock Asset ({idx+1})"))

        chosen = None
        for source in sources:
            try:
                result = source()
            except Exception as e:
                print(f"  Asset source failed for '{kw}': {e}")
                continue
            if not result:
                continue
            result = Path(result)
            if result.suffix.lower() == ".mp4" or _valid_image(result):
                chosen = result
                break
        if chosen:
            assets.append(chosen)
        else:
            print(f"  [!] No asset could be downloaded for scene {idx} ('{kw}')")

    return assets

def setup_default_assets(niche):
    """Downloads default background music if not present."""
    music_url_map = {
        "facts": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "stoicism": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
    }
    
    niche_music_path = MUSIC_DIR / f"{niche}_bg_music.mp3"
    if not niche_music_path.exists():
        url = music_url_map.get(niche)
        try:
            print(f"Downloading default copyright-free background music for {niche}...")
            download_file_with_progress(url, niche_music_path, desc=f"Bg Music ({niche})")
        except Exception as e:
            print(f"Failed to download default music: {e}")

def get_background_music(niche):
    """Returns the background music path for the niche."""
    setup_default_assets(niche)
    music_path = MUSIC_DIR / f"{niche}_bg_music.mp3"
    if not music_path.exists():
        all_music = list(MUSIC_DIR.glob("*.mp3"))
        if all_music:
            return all_music[0]
        raise FileNotFoundError("No background music found.")
    return music_path
