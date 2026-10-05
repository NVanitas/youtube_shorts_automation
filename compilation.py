"""
Weekly long-form compilation: stitches the week's published Shorts into one 16:9 video
with an intro, a title card per creature, chapters and links back to each Short.

Long-form videos earn far more per view than Shorts, count toward the 4,000 watch-hours
monetization path, and show YouTube added value beyond single clips.

Usage:
    python compilation.py --archive archive --days 7 [--upload]
"""
import os
import sys
import json
import argparse
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

load_dotenv()

if not shutil.which("ffmpeg"):
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

from config import OUTPUT_DIR
from thumbnail_generator import load_font

W, H, FPS = 1920, 1080, 30
# Identical encoding for every segment so they can be concatenated without re-encoding
ENCODE = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
# The compilation is 16:9, so YouTube never classifies it as a Short; this just keeps it substantial
MIN_TOTAL_SECONDS = 150


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
    return result


def duration_of(path):
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.stdout.strip())


def load_week(archive_dir, days, compiled_ids=()):
    """Published Shorts from the last `days` days not already in a compilation, oldest first."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    items = []
    for meta_path in sorted(Path(archive_dir).glob("*.json")):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        video = meta_path.with_suffix(".mp4")
        if meta.get("date", "") >= cutoff and video.exists() and meta.get("video_id") not in compiled_ids:
            meta["video"] = video
            items.append(meta)
    return items


def short_name(meta):
    """'cookiecutter shark' -> 'Cookiecutter Shark'; falls back to the title."""
    subjects = meta.get("subjects") or []
    if subjects:
        return " vs ".join(s.split("(")[0].strip().title() for s in subjects)
    return meta["title"].rsplit(" ", 1)[0]


def frame_from(video, at, dest):
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(at), "-i", str(video), "-frames:v", "1", str(dest)])
    return dest


def _blurred_canvas(background_frame):
    """1920x1080 darkened, blurred cover of a frame, used behind title cards and the thumbnail."""
    with Image.open(background_frame) as img:
        img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(30))
    return ImageEnhance.Brightness(img).enhance(0.4)


def _centered(draw, text, y, font, fill, stroke=6):
    width = draw.textlength(text, font=font)
    draw.text(((W - width) / 2, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill="black")


def make_card(lines, background_frame, dest_png):
    """Title card: big lines of text over a blurred frame. lines = [(text, size, color), ...]"""
    canvas = _blurred_canvas(background_frame)
    draw = ImageDraw.Draw(canvas)
    total = sum(size + 30 for _, size, _ in lines)
    y = (H - total) / 2
    for text, size, color in lines:
        _centered(draw, text, y, load_font(size), color)
        y += size + 30
    canvas.save(dest_png)
    return dest_png


def card_clip(png, seconds, dest):
    """Still image + silent audio, encoded like every other segment."""
    _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(seconds), "-i", str(png),
          "-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=48000:cl=stereo",
          "-vf", f"scale={W}:{H},fps={FPS}", *ENCODE, "-shortest", str(dest)])
    return dest


def landscape_clip(src, dest):
    """Vertical Short centered on a blurred 16:9 copy of itself."""
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:2,"
          f"eq=brightness=-0.15[bg];[0:v]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0,fps={FPS}[v]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", vf,
          "-map", "[v]", "-map", "0:a", *ENCODE, str(dest)])
    return dest


def make_thumbnail(title_text, background_frame, dest):
    canvas = _blurred_canvas(background_frame)
    canvas = ImageEnhance.Brightness(canvas).enhance(1.6)
    with Image.open(background_frame) as fg:
        fg = fg.convert("RGB")
        fg = fg.resize((int(fg.width * H / fg.height), H))
    canvas.paste(fg, (W - fg.width - 60, 0))
    draw = ImageDraw.Draw(canvas)
    # Thumbnails need 3-5 huge words, not the full title; wrap to the space left of the creature
    font = load_font(150)
    max_width = W - fg.width - 160
    words, lines = title_text.upper().split(), []
    for word in words:
        if lines and draw.textlength(f"{lines[-1]} {word}", font=font) <= max_width:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    y = (H - len(lines) * 180) / 2
    for i, line in enumerate(lines):
        draw.text((80, y), line, font=font, fill="#FFE600" if i % 2 == 0 else "white",
                  stroke_width=10, stroke_fill="black")
        y += 180
    canvas.convert("RGB").resize((1280, 720)).save(dest, "JPEG", quality=90)
    return dest


def generate_title(items):
    """Long-form title via Gemini (free tier), with a template fallback."""
    names = [short_name(i) for i in items]
    fallback = f"{len(items)} Deep Sea Creatures That Shouldn't Exist 🌊 ({names[0]}, {names[1]} & More)"
    try:
        from script_generator import _call_gemini
        prompt = ("Write ONE YouTube title (max 80 characters, 1 emoji) for a compilation video about these "
                  f"ocean creatures: {', '.join(names)}. Curiosity-driven and specific, like top documentary "
                  "channels. Mention the number of creatures. Reply with the title only.")
        title = _call_gemini(prompt, temperature=0.8, models=["gemini-2.5-flash-lite", "gemini-2.5-flash"])
        title = title.strip().strip('"').splitlines()[0]
        return title if 20 <= len(title) <= 100 else fallback
    except Exception as e:
        print(f"[COMPILATION] Title generation failed ({e}); using template.")
        return fallback


def build_compilation(items, work_dir):
    """Renders the compilation. Returns (video_path, chapters [(seconds, label)], thumbnail_frame)."""
    work_dir.mkdir(parents=True, exist_ok=True)
    segments, chapters, t = [], [], 0.0
    first_frame = frame_from(items[0]["video"], 2, work_dir / "first.jpg")

    intro = make_card([(f"{len(items)} DEEP SEA CREATURES", 120, "#FFE600"),
                       ("YOU WON'T BELIEVE ARE REAL", 80, "white")], first_frame, work_dir / "intro.png")
    segments.append(card_clip(intro, 3, work_dir / "seg_000_intro.mp4"))
    chapters.append((0, "Intro"))
    t += duration_of(segments[-1])

    for n, item in enumerate(items, 1):
        name = short_name(item)
        frame = frame_from(item["video"], 2, work_dir / f"frame_{n}.jpg")
        card = make_card([(f"#{n}", 150, "#FFE600"), (name.upper(), 95, "white")], frame, work_dir / f"card_{n}.png")
        segments.append(card_clip(card, 2, work_dir / f"seg_{n:03d}_a_card.mp4"))
        chapters.append((t, f"#{n} {name}"))
        t += duration_of(segments[-1])
        print(f"[COMPILATION] Converting #{n} {name}...")
        segments.append(landscape_clip(item["video"], work_dir / f"seg_{n:03d}_b_clip.mp4"))
        t += duration_of(segments[-1])

    outro = make_card([("NEW OCEAN SECRETS EVERY DAY", 95, "#FFE600"),
                       ("SUBSCRIBE SO YOU DON'T MISS THE NEXT ONE", 70, "white")], first_frame, work_dir / "outro.png")
    segments.append(card_clip(outro, 4, work_dir / "seg_999_outro.mp4"))
    chapters.append((t, "Subscribe for more"))

    concat_list = work_dir / "concat.txt"
    concat_list.write_text("".join(f"file '{s.resolve().as_posix()}'\n" for s in segments), encoding="utf-8")
    joined = work_dir / "joined.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
          "-c", "copy", str(joined)])

    final = work_dir / "compilation_final.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-c:v", "copy",
          "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(final)])
    return final, chapters, first_frame


def build_description(items, chapters):
    def ts(sec):
        sec = int(sec)
        return f"{sec // 60}:{sec % 60:02d}"
    lines = [f"{len(items)} of the strangest real creatures of the deep sea and prehistoric oceans - "
             "every fact checked against scientific sources.", "", "Chapters:"]
    lines += [f"{ts(sec)} {label}" for sec, label in chapters]
    lines += ["", "Watch each one as a Short:"]
    lines += [f"{short_name(i)}: {i['url']}" for i in items]
    lines += ["", "🌊 New deep sea facts every day - subscribe!", "",
              "#deepsea #ocean #marinebiology #documentary #animals"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Weekly long-form compilation of published Shorts")
    parser.add_argument("--archive", default="published", help="Folder with published .mp4/.json pairs")
    parser.add_argument("--days", type=int, default=21, help="Look-back window for Shorts not yet compiled")
    parser.add_argument("--upload", action="store_true")
    args = parser.parse_args()

    from script_generator import load_history, save_history
    history = load_history()
    items = load_week(args.archive, args.days, set(history.get("compiled_ids", [])))
    print(f"[COMPILATION] {len(items)} Shorts published in the last {args.days} days.")
    if len(items) < 5:
        print("[COMPILATION] Not enough new Shorts for a compilation yet; they will roll into next week's.")
        return
    total = sum(duration_of(i["video"]) for i in items)
    if total < MIN_TOTAL_SECONDS:
        print(f"[COMPILATION] Only {total:.0f}s of footage; needs {MIN_TOTAL_SECONDS}s to be long-form. Skipping.")
        return

    work_dir = OUTPUT_DIR / f"compilation_{datetime.now():%Y%m%d}"
    video, chapters, first_frame = build_compilation(items, work_dir)
    title = generate_title(items)
    description = build_description(items, chapters)
    thumb = make_thumbnail(f"{len(items)} REAL DEEP SEA MONSTERS", first_frame, work_dir / "thumbnail.jpg")
    print(f"[COMPILATION] Rendered {video} ({duration_of(video):.0f}s)\nTitle: {title}\n{description}")

    if args.upload:
        import youtube_uploader
        tags = list({s.split("(")[0].strip() for i in items for s in (i.get("subjects") or [])})
        tags += ["deep sea creatures", "ocean documentary", "marine biology", "sea monsters", "ocean facts"]
        url = youtube_uploader.upload_short(
            video_path=video, title=title, description=description, tags=tags[:30],
            category_id="27", privacy_status="public",
            comment_text="Which creature was the most terrifying? Tell us the number below! 👇")
        if not url:
            sys.exit(1)
        print(f"[COMPILATION] Published: {url.replace('/shorts/', '/watch?v=')} (thumbnail: {thumb.name})")
        history["compiled_ids"] = history.get("compiled_ids", []) + [i["video_id"] for i in items]
        save_history(history)


if __name__ == "__main__":
    main()
