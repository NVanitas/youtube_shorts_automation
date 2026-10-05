"""
AI Reviewer - uses Gemini (free tier) as an editor that reads the script and WATCHES the
final rendered video before upload, scoring what actually drives views on Shorts:
the hook, footage/narration match, subtitle readability, audio and factual accuracy.

Every function returns None when the API is unavailable, so the pipeline falls back to
the technical checks in quality_checker.py instead of blocking.
"""
import os
import json
import time
import requests

from script_generator import _call_gemini

API_ROOT = "https://generativelanguage.googleapis.com"

# Minimum scores (0-10) to approve
MIN_SCRIPT_SCORE = 7
MIN_VIDEO_SCORE = 6
MIN_FACT_SCORE = 7
MIN_VISUAL_SCORE = 5


def _api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    return key if key and key != "sua_chave_do_gemini_aqui" else None


def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def review_script(title, script, scenes, reference=""):
    """Scores a script before rendering, checking claims against the reference facts if given.

    Returns:
        dict: {"score": int, "passed": bool, "issues": [str]} or None if unavailable.
    """
    if not _api_key():
        return None
    scene_list = "\n".join(f"{i}: {s.get('keyword', '')}" for i, s in enumerate(scenes))
    reference_block = f"\nREFERENCE FACTS (Wikipedia) to check claims against:\n{reference}\n" if reference else ""
    prompt = f"""You are a strict YouTube Shorts editor for an English-language channel about deep sea creatures and prehistoric oceans.
Review this Short BEFORE it is produced.

TITLE: {title}
VOICEOVER SCRIPT: {script}
STOCK FOOTAGE SEARCH TERMS PER SCENE:
{scene_list}
{reference_block}
Note: the last sentence intentionally trails off (e.g. "...because") so the video loops seamlessly into the first sentence. That is a feature, not an error.

Score each 0-10:
- "hook": do the first ~8 words make a viewer stop scrolling? (vague openers like "Did you know" or "Get ready" score low)
- "facts": are ALL claims scientifically accurate? Any invented, exaggerated-to-false or unverifiable claim = max 4
- "clarity": easy to follow when heard once, at speed, with no visuals?
- "title": curiosity-driven, specific, under 70 chars, matches the script?

Respond with JSON only:
{{"hook": 0, "facts": 0, "clarity": 0, "title": 0, "issues": ["short, concrete, actionable problems; empty if none"]}}"""
    try:
        data = _parse_json(_call_gemini(prompt, temperature=0.2, json_mode=True))
    except Exception as e:
        print(f"[AI REVIEW] Script review unavailable: {e}")
        return None

    scores = {k: int(data.get(k, 0)) for k in ("hook", "facts", "clarity", "title")}
    score = round(sum(scores.values()) / len(scores), 1)
    passed = score >= MIN_SCRIPT_SCORE and scores["facts"] >= MIN_FACT_SCORE
    issues = [str(i) for i in data.get("issues", [])][:5]
    print(f"[AI REVIEW] Script: {score}/10 {scores} -> {'APPROVED' if passed else 'REJECTED'}")
    for issue in issues:
        print(f"     - {issue}")
    return {"score": score, "passed": passed, "issues": issues, "scores": scores}


def _upload_video(video_path, api_key):
    """Uploads a video to the Gemini File API and waits until it is ready."""
    size = os.path.getsize(video_path)
    start = requests.post(
        f"{API_ROOT}/upload/v1beta/files",
        headers={
            "x-goog-api-key": api_key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "Content-Type": "application/json",
        },
        json={"file": {"display_name": os.path.basename(str(video_path))}},
        timeout=60,
    )
    start.raise_for_status()
    upload_url = start.headers["x-goog-upload-url"]

    with open(video_path, "rb") as f:
        resp = requests.post(
            upload_url,
            headers={
                "Content-Length": str(size),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
            data=f.read(),
            timeout=300,
        )
    resp.raise_for_status()
    file_info = resp.json()["file"]

    for _ in range(60):
        if file_info.get("state") == "ACTIVE":
            return file_info
        if file_info.get("state") == "FAILED":
            raise RuntimeError("Gemini could not process the video file.")
        time.sleep(3)
        file_info = requests.get(f"{API_ROOT}/v1beta/{file_info['name']}", headers={"x-goog-api-key": api_key}, timeout=30).json()
    raise TimeoutError("Gemini video processing timed out.")


def review_video(video_path, title, script, scenes):
    """Has Gemini watch the rendered video and score it.

    Returns:
        dict: {"score", "passed", "scores", "bad_scenes": [{"index", "better_keyword"}],
               "issues", "script_problem": bool} or None if unavailable.
    """
    api_key = _api_key()
    if not api_key:
        return None

    file_info = None
    try:
        print("[AI REVIEW] Uploading video to Gemini for review...")
        file_info = _upload_video(video_path, api_key)
        scene_list = "\n".join(f"{i}: {s.get('keyword', '')}" for i, s in enumerate(scenes))
        prompt = f"""You are a strict YouTube Shorts editor. Watch this vertical Short (with audio) as a viewer scrolling the Shorts feed would.

TITLE: {title}
SCRIPT: {script}
The background footage is a sequence of {len(scenes)} clips shown in this order, each roughly the same length (search term used to find each clip):
{scene_list}

Notes: the script's last sentence intentionally trails off to loop into the first one (not an error). The cartoon character sticker is the channel mascot; only flag it if it covers important visuals.

Score each 0-10:
- "hook": do the first 2 seconds (visual + audio) make you stop scrolling?
- "visual_match": does each clip actually show what the narration describes at that moment? Wrong animal, people, cities, or generic unrelated footage = low
- "subtitles": readable, correctly synced, not covering important visuals or cut off?
- "audio": voice clear, music not drowning the voice, no glitches or silence gaps?
- "facts": are the spoken claims scientifically accurate?

List every clip whose footage does NOT match the narration in "bad_scenes", with a better 2-4 word stock footage search term.

Respond with JSON only:
{{"hook": 0, "visual_match": 0, "subtitles": 0, "audio": 0, "facts": 0,
  "bad_scenes": [{{"index": 0, "better_keyword": "..."}}],
  "issues": ["short, concrete problems; empty if none"]}}"""
        parts = [{"file_data": {"mime_type": "video/mp4", "file_uri": file_info["uri"]}}]
        for wait in (0, 30, 90):
            # Free-tier Gemini often returns 503 (overloaded) for a minute or two; wait it out
            time.sleep(wait)
            try:
                data = _parse_json(_call_gemini(prompt, temperature=0.2, extra_parts=parts, json_mode=True, timeout=180))
                break
            except Exception as e:
                if wait == 90:
                    raise
                print(f"[AI REVIEW] Gemini busy ({e.__class__.__name__}); retrying shortly...")
    except Exception as e:
        print(f"[AI REVIEW] Video review unavailable: {e}")
        return None
    finally:
        if file_info:
            try:
                requests.delete(f"{API_ROOT}/v1beta/{file_info['name']}", headers={"x-goog-api-key": api_key}, timeout=30)
            except Exception:
                pass

    scores = {k: int(data.get(k, 0)) for k in ("hook", "visual_match", "subtitles", "audio", "facts")}
    score = round(sum(scores.values()) / len(scores), 1)
    bad_scenes = []
    for b in data.get("bad_scenes", []):
        try:
            idx = int(b.get("index"))
            if 0 <= idx < len(scenes) and b.get("better_keyword"):
                bad_scenes.append({"index": idx, "better_keyword": str(b["better_keyword"])})
        except (TypeError, ValueError):
            pass
    # Only factual errors need a new script; a weak visual hook or wrong clips are fixed by swapping footage
    script_problem = scores["facts"] < MIN_FACT_SCORE
    passed = (score >= MIN_VIDEO_SCORE and scores["visual_match"] >= MIN_VISUAL_SCORE
              and not script_problem)
    issues = [str(i) for i in data.get("issues", [])][:6]

    print(f"[AI REVIEW] Video: {score}/10 {scores} -> {'APPROVED' if passed else 'REJECTED'}")
    for b in bad_scenes:
        print(f"     - Scene {b['index']} footage mismatch -> try '{b['better_keyword']}'")
    for issue in issues:
        print(f"     - {issue}")
    return {"score": score, "passed": passed, "scores": scores, "bad_scenes": bad_scenes,
            "issues": issues, "script_problem": script_problem}
