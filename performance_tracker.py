"""
Performance Tracker - reads real view counts of the channel's videos (YouTube Data API,
free quota, uses the existing upload token) and learns which video formats perform best.

The result is stored in the script history as:
    history["format_weights"] = {"date": "YYYY-MM-DD", "weights": {category: float},
                                 "top_titles": [best performing recent titles]}
script_generator.pick_fresh_facts_subtopic() then picks better formats more often.
"""
import pickle
from datetime import datetime, timezone, timedelta

from config import BASE_DIR

# Videos younger than this have not finished collecting views yet
MIN_AGE_DAYS = 2
# Keep exploring: no format drops below / rises above these weights
MIN_WEIGHT, MAX_WEIGHT = 0.4, 3.0


def _load_youtube_client():
    """Builds a YouTube client from token.pickle without ever opening a browser. None if unavailable."""
    token_file = BASE_DIR / "token.pickle"
    if not token_file.exists():
        return None
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    with open(token_file, "rb") as f:
        credentials = pickle.load(f)
    if not credentials.valid:
        if not (credentials.expired and credentials.refresh_token):
            return None
        credentials.refresh(Request())
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def fetch_channel_videos(youtube, max_videos=200):
    """Returns [{"id", "title", "views", "published"}] for the authenticated channel's uploads."""
    channel = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads = channel["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids, page_token = [], None
    while len(video_ids) < max_videos:
        page = youtube.playlistItems().list(part="contentDetails", playlistId=uploads,
                                            maxResults=50, pageToken=page_token).execute()
        video_ids += [i["contentDetails"]["videoId"] for i in page.get("items", [])]
        page_token = page.get("nextPageToken")
        if not page_token:
            break

    videos = []
    for i in range(0, len(video_ids), 50):
        resp = youtube.videos().list(part="snippet,statistics", id=",".join(video_ids[i:i + 50])).execute()
        for v in resp.get("items", []):
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "views": int(v["statistics"].get("viewCount", 0)),
                "published": datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00")),
            })
    return videos


def compute_format_weights(videos, title_formats, recent=60):
    """Average views per format category over the most recent settled videos, relative to the overall average."""
    from script_generator import classify_title

    cutoff = datetime.now(timezone.utc) - timedelta(days=MIN_AGE_DAYS)
    settled = sorted([v for v in videos if v["published"] < cutoff], key=lambda v: v["published"])[-recent:]
    if len(settled) < 10:
        return None

    by_cat = {}
    for v in settled:
        cat = title_formats.get(v["title"]) or classify_title(v["title"])
        by_cat.setdefault(cat, []).append(v["views"])

    overall = sum(v["views"] for v in settled) / len(settled) or 1
    weights = {}
    for cat, views in by_cat.items():
        # Shrink toward 1.0 when a category has few samples, so one viral video doesn't dominate
        avg = sum(views) / len(views)
        confidence = len(views) / (len(views) + 3)
        raw = 1.0 + confidence * (avg / overall - 1.0)
        weights[cat] = round(min(MAX_WEIGHT, max(MIN_WEIGHT, raw)), 2)

    top_titles = [v["title"] for v in sorted(settled, key=lambda v: v["views"], reverse=True)[:5]]
    stats = {cat: {"videos": len(v), "avg_views": round(sum(v) / len(v))} for cat, v in by_cat.items()}
    return {"weights": weights, "top_titles": top_titles, "stats": stats}


def refresh(history):
    """Updates history["format_weights"] at most once a day. Never raises."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if history.get("format_weights", {}).get("date") == today:
        return history
    try:
        youtube = _load_youtube_client()
        if not youtube:
            print("[PERFORMANCE] No valid YouTube token; skipping view analysis.")
            return history
        videos = fetch_channel_videos(youtube)
        result = compute_format_weights(videos, history.get("title_formats", {}))
        if not result:
            print("[PERFORMANCE] Not enough settled videos yet to learn from.")
            return history
        result["date"] = today
        history["format_weights"] = result
        print(f"[PERFORMANCE] Learned from {len(videos)} videos. Format weights: {result['weights']}")
        for cat, s in result["stats"].items():
            print(f"     - {cat}: {s['videos']} videos, avg {s['avg_views']} views")
    except Exception as e:
        print(f"[PERFORMANCE] View analysis skipped: {e}")
    return history
