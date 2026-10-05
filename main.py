import os
import sys
import re
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 on Windows to support console emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Load env variables at startup
load_dotenv()

from config import NICHES, OUTPUT_DIR
from script_generator import generate_script
from voice_generator import generate_voice
from subtitle_generator import generate_subtitles
from utils import prepare_background_assets, get_background_music
from video_composer import compose_video
import generate_whoosh

def print_banner():
    print("=" * 60)
    print("      YOUTUBE SHORTS AUTOMATION - PIPELINE GENERATOR      ")
    print("=" * 60)
    print("Target Market: English (USA/Global)")
    print("Supported Niches: ")
    print("  1. 'facts'     - Mind-Blowing Facts & Trivia")
    print("  2. 'stoicism'  - Stoic Wisdom & Motivation")
    print("=" * 60)

# Quality loop limits: each script gets up to MAX_RENDERS_PER_SCRIPT renders (bad footage is
# swapped between renders); if the script itself is the problem a new one is written.
MAX_SCRIPT_ROUNDS = 2
MAX_RENDERS_PER_SCRIPT = 2


def prepare_effects_assets():
    """Generates SFX, overlays and character stickers if missing."""
    try:
        import generate_whoosh
        import generate_impact
        import generate_overlay
        import generate_cta
        import generate_transitions
        from config import BASE_DIR
        whoosh_path = BASE_DIR / "assets" / "whoosh.wav"
        impact_path = BASE_DIR / "assets" / "impact.wav"
        grain_path = BASE_DIR / "assets" / "grain.png"
        whoosh_path.parent.mkdir(parents=True, exist_ok=True)
        generate_whoosh.generate_cinematic_whoosh(str(whoosh_path))
        generate_impact.generate_cinematic_impact(str(impact_path))
        if not grain_path.exists():
            generate_overlay.generate_cinematic_grain(str(grain_path))
        vignette_path = BASE_DIR / "assets" / "vignette.png"
        particles_path = BASE_DIR / "assets" / "particles.png"
        light_leak_path = BASE_DIR / "assets" / "light_leak.png"
        if not vignette_path.exists():
            generate_overlay.generate_cinematic_vignette(str(vignette_path))
        if not particles_path.exists():
            generate_overlay.generate_cinematic_particles(str(particles_path))
        if not light_leak_path.exists():
            generate_overlay.generate_light_leak(str(light_leak_path))
        generate_cta.generate_cta_assets(str(BASE_DIR / "assets"))
        generate_transitions.generate_all_transitions(str(BASE_DIR / "assets"))

        # Verify and generate Rexy character reaction stickers if needed
        import generate_reactions
        reactions_dir = BASE_DIR / "assets" / "reactions"
        if not reactions_dir.exists() or len(list(reactions_dir.glob("reaction_*.png"))) < 4:
            generate_reactions.generate_all_reactions()

        print("Cinematic SFX, overlays, and character stickers verified.")
    except Exception as e:
        print(f"Warning: Could not generate SFX or Overlays. {e}")


def learn_from_channel_performance():
    """Refreshes format weights from real view counts (once a day, never fatal)."""
    import performance_tracker
    from script_generator import load_history, save_history
    history = load_history()
    date_before = history.get("format_weights", {}).get("date")
    performance_tracker.refresh(history)
    if history.get("format_weights", {}).get("date") != date_before:
        save_history(history)


def replace_bad_scenes(niche_key, scenes, bg_assets, bad_scenes, video_dir, render_no, media):
    """Downloads new footage for the scenes the AI reviewer flagged as not matching the narration."""
    replaced = 0
    for bad in bad_scenes:
        idx = bad["index"]
        if idx >= len(bg_assets):
            continue
        scenes[idx]["keyword"] = bad["better_keyword"]
        retry_dir = video_dir / f"retry{render_no}_scene{idx}"
        new_assets = prepare_background_assets(niche_key, [scenes[idx]], retry_dir, media=media)
        if new_assets:
            bg_assets[idx] = new_assets[0]
            replaced += 1
    print(f"[QUALITY LOOP] Replaced footage for {replaced}/{len(bad_scenes)} flagged scenes.")
    return replaced


def run_pipeline(niche_key, topic=None, whisper_model="base", auto_upload=False):
    """Runs the complete end-to-end video creation pipeline.

    Returns:
        bool: True if a video was approved (and uploaded, when auto_upload is set).
    """
    if niche_key not in NICHES:
        print(f"Error: Niche '{niche_key}' is not configured.")
        return False

    niche_name = NICHES[niche_key]["name"]
    print(f"\n[1/6] Starting pipeline for Niche: '{niche_name}'")
    prepare_effects_assets()
    learn_from_channel_performance()

    import quality_checker
    import ai_reviewer

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    round_dirs = []
    best = None  # (ai_score, video_path, script_data) of the best fallback candidate
    approved = None
    ai_rejected_before = False

    for script_round in range(1, MAX_SCRIPT_ROUNDS + 1):
        # Create a unique directory for this script round
        suffix = "" if script_round == 1 else f"_r{script_round}"
        video_dir = OUTPUT_DIR / f"{niche_key}_{timestamp}{suffix}"
        video_dir.mkdir(parents=True, exist_ok=True)
        round_dirs.append(video_dir)
        print(f"\nVideo project directory created at: {video_dir}")

        # Step 1: Script Generation (includes AI editorial review of the script)
        script_data = generate_script(niche_key, video_dir, topic)
        if not script_data:
            print("\n[!] Script generation failed for this round. No video was created.")
            continue

        script_text = script_data["script"]
        keywords = script_data["keywords"]
        scenes = script_data["scenes"]
        print(f"\n--- GENERATED SCRIPT --- \n{script_text}")
        print(f"Keywords for assets: {keywords}\n------------------------\n")

        try:
            # Step 2: Voiceover Generation
            voiceover_path = generate_voice(niche_key, script_text, video_dir)

            # Step 3: Subtitle Generation (Whisper word-level transcription)
            print("\n[3/6] Starting audio transcription and subtitle styling...")
            subtitles_path = generate_subtitles(niche_key, voiceover_path, video_dir, keywords=keywords, model_name=whisper_model, script_text=script_text)

            # Step 4: Asset Selection (Background slideshow assets and music)
            print("\n[4/6] Loading media assets (background slideshow & music)...")
            from media_pool import MediaPool
            media = MediaPool(video_dir / "media_cache")
            bg_assets = prepare_background_assets(niche_key, scenes, video_dir, media=media)
            bg_music_path = get_background_music(niche_key)
            print(f"Background Assets ({len(bg_assets)} files): {[a.name for a in bg_assets]}")
            print(f"Background Music: {bg_music_path.name}")

            # Generate custom vertical thumbnail
            try:
                import thumbnail_generator
                gen_title = script_data.get("title", f"{niche_key.capitalize()} Daily Short")
                thumbnail_generator.generate_thumbnail(niche_key, gen_title, keywords, video_dir / "thumbnail.jpg",
                                                     background=bg_assets[0] if bg_assets else None)
            except Exception as te:
                print(f"Thumbnail generation notice: {te}")
        except Exception as e:
            print(f"Pipeline step failed for this script: {e}")
            continue

        for render_no in range(1, MAX_RENDERS_PER_SCRIPT + 1):
            # Step 5: Video Composition + audio loudness normalization
            print(f"\n[5/6] Compiling final video (script {script_round}, render {render_no})...")
            try:
                final_video = compose_video(niche_key, bg_assets, voiceover_path, bg_music_path, subtitles_path, video_dir, scenes=scenes)
                quality_checker.normalize_loudness(final_video)
            except Exception as e:
                print(f"Video composition failed: {e}")
                break

            # Step 6: Quality Gate (technical checks + AI editor watching the video)
            print("\n[6/6] Running quality analysis...")
            report = quality_checker.analyze(
                video_path=final_video,
                subtitles_ass_path=subtitles_path,
                script_text=script_text,
                bg_assets=bg_assets
            )
            tech_passed = quality_checker.print_report(report)
            review = ai_reviewer.review_video(final_video, script_data["title"], script_text, scenes)

            candidate = video_dir / f"candidate_{render_no}.mp4"
            shutil.copy(final_video, candidate)
            # Without AI review only the technical gate applies - but a temporary API outage must not
            # approve a video after the AI already rejected an earlier render in this run
            ai_ok = review["passed"] if review else not ai_rejected_before
            if review and not review["passed"]:
                ai_rejected_before = True
            if tech_passed and ai_ok:
                approved = (candidate, script_data, video_dir)
                break
            near_miss = (tech_passed and review and not review["script_problem"]
                         and review["scores"]["visual_match"] >= ai_reviewer.MIN_VISUAL_SCORE - 1)
            if near_miss and (best is None or review["score"] > best[0]):
                best = (review["score"], candidate, script_data, video_dir)

            if review and review["script_problem"]:
                print("[QUALITY LOOP] Script problem (hook/facts). Writing a new script...")
                break
            if review and review["bad_scenes"] and render_no < MAX_RENDERS_PER_SCRIPT:
                replace_bad_scenes(niche_key, scenes, bg_assets, review["bad_scenes"], video_dir, render_no, media)
                continue
            break

        if approved:
            break

    # Accept the best near-miss rather than skipping the day, but never one with factual/hook problems
    if not approved and best and best[0] >= ai_reviewer.MIN_VIDEO_SCORE - 1:
        print(f"\n[QUALITY LOOP] No render fully approved; using best candidate (AI score {best[0]}/10).")
        approved = best[1:]

    if not approved:
        print("\n" + "=" * 60)
        print("[QUALITY GATE] NO VIDEO APPROVED - nothing will be uploaded today.")
        print(f"   Renders kept for inspection in: {[d.name for d in round_dirs]}")
        print("=" * 60)
        return False

    final_video, script_data, video_dir = approved
    print("\n" + "=" * 60)
    print("[SUCCESS] Your YouTube Short has been generated and approved!")
    print(f"   Video saved to: {final_video}")
    print("=" * 60)

    if not auto_upload:
        return True
    uploaded_url = upload_video(niche_key, script_data, final_video)
    if uploaded_url:
        archive_published_short(final_video, script_data, uploaded_url)
        # Clean up local project directories to save space if upload was successful
        print(f"\n[CLEANUP] Deleting local video files to save disk space...")
        import gc
        gc.collect()
        for d in round_dirs:
            shutil.rmtree(str(d), ignore_errors=True)
    return bool(uploaded_url)


def archive_published_short(final_video, script_data, url):
    """Keeps a copy of every published Short in published/ (uploaded by CI to the 'shorts-archive'
    GitHub release) for the weekly long-form compilation and for reposting on TikTok/Reels."""
    import json
    from config import BASE_DIR
    published = BASE_DIR / "published"
    published.mkdir(exist_ok=True)
    video_id = url.rstrip("/").split("/")[-1]
    stem = f"{datetime.now():%Y-%m-%d}_{video_id}"
    shutil.copy(final_video, published / f"{stem}.mp4")
    subjects = script_data.get("subjects") or []
    hashtags = [re.sub(r"[^a-z0-9]", "", s.split("(")[0].lower()) for s in subjects]
    hashtags = [h for h in hashtags if h] + ["deepsea", "ocean", "marinebiology", "animalfacts", "fyp"]
    meta = {
        "video_id": video_id,
        "url": url,
        "date": f"{datetime.now():%Y-%m-%d}",
        "title": script_data.get("title", ""),
        "script": script_data.get("script", ""),
        "subjects": subjects,
        # Ready-to-paste caption for TikTok / Instagram Reels
        "social_caption": f"{script_data.get('title', '')} " + " ".join(f"#{h}" for h in hashtags),
    }
    with open(published / f"{stem}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    (published / f"{stem}_caption.txt").write_text(meta["social_caption"], encoding="utf-8")
    print(f"[ARCHIVE] Saved published/{stem}.mp4 for compilations and cross-posting.")


def upload_video(niche_key, script_data, final_video):
    """Uploads the approved video with title, tags, description and a pinned-style first comment."""
    print("\n[YOUTUBE AUTOMATION] Initiating upload process...")
    script_text = script_data["script"]
    try:
        import youtube_uploader

        # Extract dynamically generated viral title or use niche fallback
        generated_title = script_data.get("title", "").strip()

        if niche_key == "facts":
            video_title = generated_title if generated_title else "3 Mind-Blowing Facts You Did Not Know 🤯 #shorts"
            # Specific hashtags tell YouTube which audience to test the Short on; the first 3 show above the title
            subject_tags = [re.sub(r"[^a-z0-9]", "", s.split("(")[0].lower()) for s in script_data.get("subjects") or []]
            hashtags = [t for t in subject_tags if t][:2] + ["deepsea", "ocean", "marinebiology", "animals", "shorts"]
            tags = [s.split("(")[0].strip() for s in script_data.get("subjects") or []] + [
                "deep sea", "ocean animals", "marine biology", "sea creatures", "animal facts",
                "prehistoric ocean", "ocean facts", "shorts"]
            cat_id = "27" # Education
            video_description = (f"{generated_title}\n\n{script_text}\n\n"
                                 "🌊 New deep sea & prehistoric ocean facts every day - subscribe so you don't miss the next one!\n\n"
                                 + " ".join(f"#{h}" for h in hashtags))
        else:
            video_title = generated_title if generated_title else "How to Master Your Mind (Stoic Wisdom) 🏛️ #shorts"
            tags = ["shorts", "viral", "fyp", "stoicism", "motivation", "ancientwisdom", "discipline", "mindset"]
            cat_id = "22" # People & Blogs / Motivation
            video_description = f"{script_text}\n\nSubscribe to the channel for daily Shorts!\n\n#shorts #stoicism #motivation #ancientwisdom"

        # Build smart pinned comment based on script content
        if niche_key == "facts":
            sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
            question_sentences = [s.strip() for s in sentences if "?" in s]

            # Detect format type from subtopic/script keywords
            is_duel = any(w in script_text.lower() for w in ["vs", "versus", "duel", "battle", "fight", "wins", "who would"])
            is_quiz = any(w in script_text.lower() for w in ["true or false", "guess", "fake", "real or fake", "which one"])

            if is_duel and question_sentences:
                comment_text = f"{question_sentences[-1]} Team A or Team B - drop your answer below! 👇"
            elif is_quiz:
                comment_text = "Did you guess the fake one? Drop your answer below - no cheating! 👇"
            elif question_sentences:
                comment_text = f"{question_sentences[-1]} Drop your answer below! 👇"
            else:
                comment_text = "Which of these bizarre deep-sea facts blew your mind the most? Comment below! 👇"
        else:
            comment_text = "Which Stoic lesson do you need most right now? Comment below! 👇"

        return youtube_uploader.upload_short(
            video_path=final_video,
            title=video_title,
            description=video_description,
            tags=tags,
            category_id=cat_id,
            privacy_status="public",
            comment_text=comment_text
        )
    except Exception as ue:
        print(f"\n[YOUTUBE UPLOAD ERROR] Upload failed: {ue}")
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            raise ue
        return None

def main():
    print_banner()
    
    # CLI argument parsing
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Pipeline")
    parser.add_argument("--niche", choices=["facts", "stoicism"], help="The niche to generate a video for")
    parser.add_argument("--topic", type=str, help="Specific topic or theme for the script (optional)")
    parser.add_argument("--upload", action="store_true", help="Automatically upload generated video to YouTube")
    parser.add_argument("--whisper-model", type=str, default="base", 
                        choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size for transcription (default: base)")
    
    args = parser.parse_args()
    
    if args.niche:
        ok = run_pipeline(args.niche, args.topic, args.whisper_model, auto_upload=args.upload)
        # Make the scheduled GitHub Actions run show as failed when nothing was published
        if args.upload and not ok and (os.getenv("CI") or os.getenv("GITHUB_ACTIONS")):
            sys.exit(1)
    else:
        # Semi-Automatic Mode: User chooses the niche, the rest is automatic
        print("Select a niche:")
        print("1. Mind-Blowing Facts ('facts')")
        print("2. Stoic Wisdom & Motivation ('stoicism')")
        
        choice = input("\nEnter your choice (1 or 2): ").strip()
        niche_key = "facts" if choice == "1" else "stoicism" if choice == "2" else None
        
        if not niche_key:
            print("Invalid selection. Exiting.")
            sys.exit(1)
            
        upload_choice = input("Do you want to automatically upload this video to YouTube upon completion? (y/N): ").strip().lower()
        auto_upload = upload_choice.startswith("y")
        
        print(f"\n[AUTOMATIC MODE] ENGAGED FOR NICHE: {niche_key.upper()}")
        
        topic = None
        whisper_model = "base"
        
        run_pipeline(niche_key, topic, whisper_model, auto_upload=auto_upload)

if __name__ == "__main__":
    main()
