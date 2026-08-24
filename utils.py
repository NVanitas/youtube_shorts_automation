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

def download_pexels_video(query, dest_path, api_key):
    """Searches and downloads a vertical video from Pexels API matching the query."""
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": 5,
        "orientation": "portrait"
    }
    
    try:
        response = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        videos = data.get("videos", [])
        if not videos:
            print(f"No videos found on Pexels for query '{query}'")
            return None
            
        # Select the first video or a random one from results
        video_data = random.choice(videos)
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
        return dest_path
    except Exception as e:
        print(f"Failed to download video from Pexels for '{query}': {e}")
        return None

def prepare_background_assets(niche_key, scenes, video_dir):
    """Downloads or prepares background assets matching the script scenes.
    
    For 'facts' niche, prioritizes stock VIDEO footage from Pexels
    (the character is overlaid separately as a PNG sticker).
    
    Returns:
        list of Path: List of paths to the downloaded media assets
    """
    pexels_key = os.getenv("PEXELS_API_KEY")
    assets = []
    
    assets_dir = video_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
            
    print(f"\nPreparing background assets for {len(scenes)} scenes:")
    for idx, scene in enumerate(scenes):
        kw = scene["keyword"]
        
        if pexels_key:
            # Try to download stock video first (preferred for all niches now)
            video_dest = assets_dir / f"bg_asset_{idx}.mp4"
            downloaded = download_pexels_video(kw, video_dest, pexels_key)
            if downloaded:
                assets.append(downloaded)
                continue
            print(f"  No Pexels video for '{kw}', falling back to AI image...")
            
        # Fallback: Generate AI image (scenic background only, no character)
        prompt_text = f"{kw} cinematic vertical hd dramatic lighting"
        image_dest = assets_dir / f"bg_asset_{idx}.jpg"
        downloaded = download_ai_image(prompt_text, image_dest)
        
        # Verify image integrity
        valid_asset = False
        if downloaded and downloaded.exists():
            try:
                from PIL import Image
                with Image.open(downloaded) as img:
                    img.verify()
                valid_asset = True
            except Exception:
                valid_asset = False
                
        if valid_asset:
            assets.append(image_dest)
        else:
            # High-quality HD Stock fallback guarantee
            print(f"Guaranteeing HD Stock asset for '{kw}'...")
            guaranteed_urls = [
                f"https://picsum.photos/seed/{idx+100}/1080/1920",
                f"https://picsum.photos/1080/1920"
            ]
            for g_url in guaranteed_urls:
                try:
                    download_file_with_progress(g_url, image_dest, desc=f"HD Stock Asset ({idx+1})")
                    from PIL import Image
                    with Image.open(image_dest) as img:
                        img.verify()
                    assets.append(image_dest)
                    valid_asset = True
                    break
                except Exception:
                    pass
                    
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
