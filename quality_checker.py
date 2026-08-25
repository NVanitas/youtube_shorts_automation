"""
Quality Checker — Analisa o vídeo final e atribui uma nota de 0-100.
Só permite publicação se a nota for >= threshold configurável.
Usa ffprobe (do static-ffmpeg) para extrair metadados reais do arquivo.
"""
import subprocess
import json
from pathlib import Path
import shutil

if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

# Minimum score to approve a video for upload
MIN_SCORE = 70


def _probe(filepath):
    """Run ffprobe and return parsed JSON metadata."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(filepath)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def _analyze_internal(video_path, subtitles_ass_path=None, script_text=None, min_score=MIN_SCORE):
    """
    Analyze a rendered video and return a quality report dict.

    Returns:
        dict with keys: score, passed, checks (list of dicts), suggestions (list of str)
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return {"score": 0, "passed": False, "checks": [], "suggestions": ["Video file not found."]}

    probe = _probe(video_path)
    if not probe:
        return {"score": 0, "passed": False, "checks": [], "suggestions": ["ffprobe failed to read the file."]}

    checks = []
    suggestions = []
    total = 0

    # --- 1. Resolution check (max 20 pts) ---
    video_stream = next((s for s in probe.get("streams", []) if s["codec_type"] == "video"), None)
    if video_stream:
        w = int(video_stream.get("width", 0))
        h = int(video_stream.get("height", 0))
        if w == 1080 and h == 1920:
            pts = 20
            checks.append({"name": "Resolution", "value": f"{w}x{h}", "status": "✓", "pts": pts})
        elif w >= 720 and h >= 1280:
            pts = 12
            checks.append({"name": "Resolution", "value": f"{w}x{h}", "status": "~", "pts": pts})
            suggestions.append(f"Resolution is {w}x{h}. Ideal is 1080x1920 for Shorts/TikTok.")
        else:
            pts = 0
            checks.append({"name": "Resolution", "value": f"{w}x{h}", "status": "✗", "pts": pts})
            suggestions.append(f"Resolution {w}x{h} is too low. Must be at least 720x1280.")
        total += pts
    else:
        checks.append({"name": "Resolution", "value": "N/A", "status": "✗", "pts": 0})
        suggestions.append("No video stream found in file.")

    # --- 2. Duration check (max 15 pts) ---
    duration = float(probe.get("format", {}).get("duration", 0))
    if 15 <= duration <= 60:
        pts = 15
        checks.append({"name": "Duration", "value": f"{duration:.1f}s", "status": "✓", "pts": pts})
    elif 10 <= duration < 15 or 60 < duration <= 90:
        pts = 8
        checks.append({"name": "Duration", "value": f"{duration:.1f}s", "status": "~", "pts": pts})
        suggestions.append(f"Duration is {duration:.1f}s. Ideal range for Shorts is 15-60s.")
    else:
        pts = 0
        checks.append({"name": "Duration", "value": f"{duration:.1f}s", "status": "✗", "pts": pts})
        suggestions.append(f"Duration {duration:.1f}s is outside acceptable range (15-60s).")
    total += pts

    # --- 3. Video bitrate check (max 20 pts) ---
    if video_stream:
        # Try stream bitrate first, then calculate from file size
        vbr = int(video_stream.get("bit_rate", 0))
        if vbr == 0 and duration > 0:
            file_size = int(probe.get("format", {}).get("size", 0))
            vbr = int((file_size * 8) / duration)
        vbr_mbps = vbr / 1_000_000

        if vbr_mbps >= 3.0:
            pts = 20
            checks.append({"name": "Video Bitrate", "value": f"{vbr_mbps:.1f} Mbps", "status": "✓", "pts": pts})
        elif vbr_mbps >= 1.5:
            pts = 12
            checks.append({"name": "Video Bitrate", "value": f"{vbr_mbps:.1f} Mbps", "status": "~", "pts": pts})
            suggestions.append(f"Video bitrate is {vbr_mbps:.1f} Mbps. >= 3 Mbps recommended for crisp quality.")
        else:
            pts = 5
            checks.append({"name": "Video Bitrate", "value": f"{vbr_mbps:.1f} Mbps", "status": "✗", "pts": pts})
            suggestions.append(f"Video bitrate {vbr_mbps:.1f} Mbps is very low. Quality will look blurry.")
        total += pts

    # --- 4. Audio bitrate check (max 15 pts) ---
    audio_stream = next((s for s in probe.get("streams", []) if s["codec_type"] == "audio"), None)
    if audio_stream:
        abr = int(audio_stream.get("bit_rate", 0))
        abr_kbps = abr / 1000

        if abr_kbps >= 128:
            pts = 15
            checks.append({"name": "Audio Bitrate", "value": f"{abr_kbps:.0f} kbps", "status": "✓", "pts": pts})
        elif abr_kbps >= 64:
            pts = 8
            checks.append({"name": "Audio Bitrate", "value": f"{abr_kbps:.0f} kbps", "status": "~", "pts": pts})
            suggestions.append(f"Audio bitrate is {abr_kbps:.0f} kbps. >= 128 kbps recommended.")
        else:
            pts = 3
            checks.append({"name": "Audio Bitrate", "value": f"{abr_kbps:.0f} kbps", "status": "✗", "pts": pts})
            suggestions.append(f"Audio bitrate {abr_kbps:.0f} kbps is low. Audio will sound muffled.")
        total += pts
    else:
        checks.append({"name": "Audio Bitrate", "value": "N/A", "status": "✗", "pts": 0})
        suggestions.append("No audio stream found.")

    # --- 5. Subtitles check (max 15 pts) ---
    if subtitles_ass_path and Path(subtitles_ass_path).exists():
        with open(subtitles_ass_path, "r", encoding="utf-8") as f:
            ass_content = f.read()
        dialogue_count = ass_content.count("Dialogue:")
        if dialogue_count >= 5:
            pts = 15
            checks.append({"name": "Subtitles", "value": f"{dialogue_count} lines", "status": "✓", "pts": pts})
        elif dialogue_count >= 1:
            pts = 8
            checks.append({"name": "Subtitles", "value": f"{dialogue_count} lines", "status": "~", "pts": pts})
            suggestions.append(f"Only {dialogue_count} subtitle lines. Script may be too short.")
        else:
            pts = 0
            checks.append({"name": "Subtitles", "value": "Empty", "status": "✗", "pts": pts})
            suggestions.append("Subtitle file exists but has no dialogue lines.")
        total += pts
    else:
        checks.append({"name": "Subtitles", "value": "Missing", "status": "✗", "pts": 0})
        suggestions.append("No subtitle file found. Subtitles are critical for engagement.")

    # --- 6. CTA check (max 15 pts) ---
    if script_text:
        script_lower = script_text.lower()
        has_cta = any(kw in script_lower for kw in ["subscribe", "like", "follow", "channel"])
        if has_cta:
            pts = 15
            checks.append({"name": "CTA (Call to Action)", "value": "Detected", "status": "✓", "pts": pts})
        else:
            pts = 5
            checks.append({"name": "CTA (Call to Action)", "value": "Not found", "status": "~", "pts": pts})
            suggestions.append("No subscribe/like CTA detected in script. Add one for better conversion.")
        total += pts
    else:
        checks.append({"name": "CTA (Call to Action)", "value": "N/A", "status": "~", "pts": 10})
        total += 10  # Assume present if we can't check

    passed = total >= min_score

    return {
        "score": total,
        "max_score": 100,
        "passed": passed,
        "min_score": min_score,
        "checks": checks,
        "suggestions": suggestions
    }

def analyze(video_path, subtitles_ass_path=None, script_text=None, bg_assets=None, min_score=MIN_SCORE):
    """
    Analyze a rendered video and return a quality report dict.
    """
    report = _analyze_internal(video_path, subtitles_ass_path, script_text, min_score)
    
    # Verify Background Asset Integrity if provided
    if bg_assets:
        corrupt_count = 0
        for asset in bg_assets:
            asset_path = Path(asset)
            if not asset_path.exists() or asset_path.stat().st_size == 0:
                corrupt_count += 1
                
        if corrupt_count > 0:
            report["passed"] = False
            report["score"] = max(0, report["score"] - 40)
            report["checks"].append({"name": "Asset Integrity", "value": f"{corrupt_count} Corrupt", "status": "✗", "pts": 0})
            report["suggestions"].append(f"CRITICAL: {corrupt_count} background assets are missing or corrupted. Upload aborted.")
        else:
            report["checks"].append({"name": "Asset Integrity", "value": f"{len(bg_assets)} Valid HD", "status": "✓", "pts": 10})
            
    return report

def print_report(report):
    """Print a formatted quality report to the console."""
    print("\n" + "=" * 50)
    print("      VIDEO QUALITY REPORT")
    print("=" * 50)

    for check in report["checks"]:
        raw_status = check["status"]
        # Convert non-ascii markers to safe ascii equivalents
        if raw_status == "✓":
            status = "[OK]  "
        elif raw_status == "~":
            status = "[WARN]"
        else:
            status = "[FAIL]"
            
        name = check["name"].ljust(18)
        value = check["value"].ljust(14)
        pts = f"+{check['pts']} pts"
        print(f"  {status}  {name} {value} {pts}")

    print("-" * 50)
    score = report["score"]
    max_score = report["max_score"]
    passed = report["passed"]

    if passed:
        print(f"  TOTAL: {score}/{max_score}  [PASSED] APPROVED FOR UPLOAD")
    else:
        print(f"  TOTAL: {score}/{max_score}  [FAILED] DISAPPROVED (min: {report['min_score']})")

    if report["suggestions"]:
        print("\n  Suggestions for improvement:")
        for s in report["suggestions"]:
            print(f"     - {s}")

    print("=" * 50 + "\n")
    return passed
