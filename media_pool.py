"""
Media Pool - builds, once per video, a pool of DISTINCT real media of a species from
Wikipedia / Wikimedia Commons (free, no API key): the article's photos plus Commons
videos (often public-domain NOAA deep-sea footage) and photos.

Scenes take items from the pool in order, so no image is shown twice in one video.
Requests are batched (3 per species) with backoff, because Wikimedia rate-limits (429)
bursts of anonymous requests.
"""
import re
import time
import shutil
import subprocess
from pathlib import Path

import requests

if not shutil.which("ffmpeg"):
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

HTTP_HEADERS = {"User-Agent": "NicosaurusShortsBot/1.0 (educational YouTube channel; github.com/NVanitas)"}
WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

NON_PHOTO_WORDS = ("map", "diagram", "distribution", "range", "drawing", "illustration", "label", "logo",
                   "location", "chart", "figure", "fig.", "graph", "plot", "schem", "sketch", "plate",
                   "stamp", "icon", "flag", "coat of arms", "skeleton", "fossil", "jaw", "tooth", "teeth")
VIDEO_MIMES = ("video/webm", "application/ogg", "video/ogg", "video/mp4")
IMAGE_MIMES = ("image/jpeg", "image/png")

# Seconds of footage cut from each Commons video per scene
CLIP_SECONDS = 8


def _api_get(url, params, retries=3):
    """GET a MediaWiki API with polite pacing and 429 backoff. Returns parsed JSON or None."""
    params = {"format": "json", "formatversion": 2, **params}
    for attempt in range(retries + 1):
        time.sleep(1.0)
        try:
            resp = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=25)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"[MEDIA] Wikimedia rate limit, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[MEDIA] Wikimedia request failed: {e}")
            time.sleep(3)
    return None


def _is_usable(title, info, required_tokens=None):
    t = title.lower()
    if any(w in t for w in NON_PHOTO_WORDS):
        return False
    if required_tokens and not all(tok in t for tok in required_tokens):
        return False
    mime = info.get("mime", "")
    if mime in IMAGE_MIMES:
        # >= 960 so the API returns a standard-size thumbnail (originals are heavily rate-limited)
        return info.get("width", 0) > 960
    if mime in VIDEO_MIMES:
        return info.get("duration", 0) >= 4 and info.get("width", 0) >= 400
    return False


def _items_from_pages(pages, required_tokens=None):
    items = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        if not _is_usable(page.get("title", ""), info, required_tokens):
            continue
        is_video = info.get("mime") in VIDEO_MIMES
        items.append({
            "kind": "video" if is_video else "image",
            "url": info.get("url") if is_video else (info.get("thumburl") or info.get("url")),
            "title": page.get("title", ""),
            "duration": info.get("duration", 0),
            "size": info.get("size", 0),
        })
    return items


def build_species_pool(species):
    """Returns a list of distinct media items for a species, videos first."""
    name = species.split("(")[0].strip()
    tokens = [t for t in re.findall(r"[a-z]+", name.lower()) if len(t) > 2]
    iiprops = {"prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 960}

    # 1. Wikipedia article: all images/videos used in it (curated, almost always the right animal)
    article_items = []
    found = _api_get(WIKI_API, {"action": "query", "list": "search", "srsearch": name, "srlimit": 1})
    hits = (found or {}).get("query", {}).get("search", [])
    if hits:
        data = _api_get(WIKI_API, {"action": "query", "titles": hits[0]["title"], "generator": "images",
                                   "gimlimit": 40, **iiprops})
        article_items = _items_from_pages((data or {}).get("query", {}).get("pages", []))

    # 2. Commons search: videos and photos whose file name names the species
    data = _api_get(COMMONS_API, {"action": "query", "generator": "search", "gsrnamespace": 6, "gsrlimit": 40,
                                  "gsrsearch": f"{name} filetype:video|bitmap", **iiprops})
    commons_items = _items_from_pages((data or {}).get("query", {}).get("pages", []), tokens)

    pool, seen = [], set()
    for item in article_items + commons_items:
        if item["url"] and item["url"] not in seen:
            seen.add(item["url"])
            pool.append(item)
    pool.sort(key=lambda i: 0 if i["kind"] == "video" else 1)
    n_videos = sum(1 for i in pool if i["kind"] == "video")
    print(f"[MEDIA] Pool for '{name}': {n_videos} videos, {len(pool) - n_videos} photos")
    return pool


def _transcoded_urls(original_url):
    """Wikimedia serves smaller transcodes of every video; prefer those over multi-GB originals."""
    original_url = original_url.split("?")[0]  # API URLs carry utm_* tracking params
    m = re.match(r"(https://upload\.wikimedia\.org/wikipedia/commons)/(\w/\w\w)/(.+)$", original_url)
    if not m:
        return [original_url]
    base, hashdir, fname = m.groups()
    t = f"{base}/transcoded/{hashdir}/{fname}/{fname}"
    # Low-resolution sources only have the smaller transcodes; the original is the last resort (size-capped)
    return [f"{t}.{res}{codec}.webm" for res in ("720p", "480p", "360p") for codec in (".vp9", "")] + [original_url]


def _download(url, dest, max_mb=150):
    for attempt in range(3):
        # upload.wikimedia.org rate-limits bursts: pace downloads and back off on 429
        time.sleep(1.5 + 8 * attempt)
        resp = requests.get(url, headers=HTTP_HEADERS, stream=True, timeout=60)
        if resp.status_code != 429:
            break
        resp.close()
    with resp:
        resp.raise_for_status()
        if int(resp.headers.get("content-length", 0)) > max_mb * 1024 * 1024:
            raise ValueError("file too large")
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(1 << 16):
                f.write(chunk)
    return dest


def make_vertical_clip(src, dest, start=0.0, seconds=CLIP_SECONDS):
    """Cuts a segment and turns it into a 1080x1920 mp4: the full frame over a blurred copy of itself."""
    vf = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2,"
          "eq=brightness=-0.12[bg];[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(src), "-t", str(seconds),
           "-filter_complex", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(dest)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not Path(dest).exists() or Path(dest).stat().st_size < 10_000:
        raise RuntimeError(f"ffmpeg clip failed: {result.stderr[-200:]}")
    return Path(dest)


class MediaPool:
    """Hands out distinct media for scenes. Long videos can supply several different segments."""

    def __init__(self, work_dir):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.pools = {}
        self.used_urls = set()
        self.video_cache = {}   # url -> (local source path, duration, next segment start)
        self.failed = set()
        self.use_count = {}

    def _pool(self, species):
        if species not in self.pools:
            self.pools[species] = build_species_pool(species)
        return self.pools[species]

    def _video_segment(self, item, dest):
        url = item["url"]
        if url not in self.video_cache:
            src = self.work_dir / f"src_{len(self.video_cache)}.webm"
            for candidate in _transcoded_urls(url):
                try:
                    _download(candidate, src)
                    break
                except Exception:
                    continue
            else:
                self.failed.add(url)
                return None
            self.video_cache[url] = [src, float(item.get("duration") or 0), 1.0]
        src, duration, start = self.video_cache[url]
        if duration and start + 3 > duration:
            return None
        clip = make_vertical_clip(src, dest, start=start)
        # Next scene from this video starts further in, so it shows different footage
        self.video_cache[url][2] = start + CLIP_SECONDS + 2
        return clip

    def next_asset(self, species, dest_stem):
        """Returns a local path (mp4 or jpg) of media not yet used in this video, or None."""
        from utils import fit_vertical
        # Videos before photos (motion holds viewers), least-used first so sources alternate
        pool = sorted(self._pool(species), key=lambda i: (i["kind"] != "video", self.use_count.get(i["url"], 0)))
        for item in pool:
            key = item["url"]
            uses = self.use_count.get(key, 0)
            # A long video may supply up to 2 different segments; a photo is used only once
            if key in self.failed or uses >= (2 if item["kind"] == "video" else 1):
                continue
            try:
                if item["kind"] == "video":
                    path = self._video_segment(item, Path(f"{dest_stem}.mp4"))
                    if not path:
                        continue
                else:
                    path = _download(key, Path(f"{dest_stem}.jpg"), max_mb=25)
                    fit_vertical(path)
                self.used_urls.add(key)
                self.use_count[key] = uses + 1
                print(f"[MEDIA] {Path(path).name} <- {item['kind']}: {item['title'][:70]}")
                return Path(path)
            except Exception as e:
                print(f"[MEDIA] Skipping {item['title'][:60]}: {e}")
                self.failed.add(key)
        return None
