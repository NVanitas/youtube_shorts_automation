import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

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

def run_pipeline(niche_key, topic=None, whisper_model="base", auto_upload=False):
    """Runs the complete end-to-end video creation pipeline."""
    if niche_key not in NICHES:
        print(f"Error: Niche '{niche_key}' is not configured.")
        return
        
    niche_name = NICHES[niche_key]["name"]
    print(f"\n[1/5] Starting pipeline for Niche: '{niche_name}'")
    
    # Auto-generate a fresh, high-quality cinematic whoosh sound and impact sound
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
        print("Cinematic SFX and overlays generated successfully.")
    except Exception as e:
        print(f"Warning: Could not generate SFX or Overlays. {e}")
    
    # Create a unique directory for this video
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    video_dir = OUTPUT_DIR / f"{niche_key}_{timestamp}"
    video_dir.mkdir(parents=True, exist_ok=True)
    print(f"Video project directory created at: {video_dir}")
    
    # Step 1: Script Generation
    script_data = generate_script(niche_key, video_dir, topic)
    if not script_data:
        print("\n[!] Pipeline stopped: Script generation failed. No video was created.")
        return
        
    script_text = script_data["script"]
    keywords = script_data["keywords"]
    print(f"\n--- GENERATED SCRIPT --- \n{script_text}")
    print(f"Keywords for assets: {keywords}\n------------------------\n")
    
    # Step 2: Voiceover Generation
    try:
        voiceover_path = generate_voice(niche_key, script_text, video_dir)
    except Exception as e:
        print(f"Pipeline stopped: Voiceover generation failed. {e}")
        return
        
    # Step 3: Subtitle Generation (Whisper word-level transcription)
    print("\n[3/5] Starting audio transcription and subtitle styling...")
    try:
        subtitles_path = generate_subtitles(niche_key, voiceover_path, video_dir, keywords=keywords, model_name=whisper_model)
    except Exception as e:
        print(f"Pipeline stopped: Subtitle generation failed. {e}")
        return
        
    # Step 4: Asset Selection (Background slideshow assets and music)
    print("\n[4/5] Loading media assets (background slideshow & music)...")
    try:
        bg_assets = prepare_background_assets(niche_key, keywords, video_dir)
        bg_music_path = get_background_music(niche_key)
        print(f"Background Assets ({len(bg_assets)} files): {[a.name for a in bg_assets]}")
        print(f"Background Music: {bg_music_path.name}")
    except Exception as e:
        print(f"Pipeline stopped: Asset preparation failed. {e}")
        return
        
    # Step 5: High-CTR Thumbnail Generation & Video Composition
    print("\n[5/5] Generating high-CTR thumbnail and compiling final video...")
    try:
        # Generate custom vertical thumbnail first
        thumb_path = video_dir / "thumbnail.jpg"
        try:
            import thumbnail_generator
            gen_title = script_data.get("title", f"{niche_key.capitalize()} Daily Short")
            thumbnail_generator.generate_thumbnail(niche_key, gen_title, keywords, thumb_path)
        except Exception as te:
            print(f"Thumbnail generation notice: {te}")
            
        final_video = compose_video(niche_key, bg_assets, voiceover_path, bg_music_path, subtitles_path, video_dir)
        
        # Step 6: Quality Gate
        print("\n[6/6] Running quality analysis...")
        import quality_checker
        report = quality_checker.analyze(
            video_path=final_video,
            subtitles_ass_path=subtitles_path,
            script_text=script_text,
            bg_assets=bg_assets
        )
        passed = quality_checker.print_report(report)
        
        if passed:
            print("\n" + "=" * 60)
            print("[SUCCESS] Your YouTube Short has been generated!")
            print(f"   Video saved to: {final_video}")
            print(f"   Quality Score:  {report['score']}/100")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("[WARNING] VIDEO GENERATED BUT DID NOT PASS QUALITY CHECK")
            print(f"   Video saved to: {final_video}")
            print(f"   Score: {report['score']}/100 (minimum: {report['min_score']})")
            print("   Review the suggestions above before uploading.")
            print("=" * 60)
            
        # Step 7: Automatic YouTube Upload
        if auto_upload:
            print("\n[YOUTUBE AUTOMATION] Initiating upload process...")
            import youtube_uploader
            
            # Extract dynamically generated viral title or use niche fallback
            generated_title = script_data.get("title", "").strip()
            
            if niche_key == "facts":
                video_title = generated_title if generated_title else "3 Mind-Blowing Facts You Did Not Know 🤯 #shorts"
                tags = ["shorts", "viral", "fyp", "facts", "mindblowing", "science", "trivia", "didyouknow"]
                cat_id = "27" # Education
            else:
                video_title = generated_title if generated_title else "How to Master Your Mind (Stoic Wisdom) 🏛️ #shorts"
                tags = ["shorts", "viral", "fyp", "stoicism", "motivation", "ancientwisdom", "discipline", "mindset"]
                cat_id = "22" # People & Blogs / Motivation
                
            video_description = f"{script_text}\n\nSubscribe to the channel for daily Shorts!\n\n#shorts #viral #fyp #{niche_key} #motivation #educational"
            
            # Define first automated comment text
            comment_text = "Which of these facts surprised you the most? Comment below! 👇" if niche_key == "facts" else "Which lesson do you need most in your life right now? Comment below! 👇"

            uploaded_url = youtube_uploader.upload_short(
                video_path=final_video,
                title=video_title,
                description=video_description,
                tags=tags,
                category_id=cat_id,
                privacy_status="public",
                comment_text=comment_text
            )

            # Clean up local project directory to save space if upload was successful
            if uploaded_url and video_dir.exists():
                print(f"\n[CLEANUP] Deleting local video files to save disk space: {video_dir.name}")
                try:
                    import shutil
                    # Close video reader resources before deleting directory
                    import gc
                    gc.collect()
                    shutil.rmtree(str(video_dir))
                    print("[CLEANUP] Local files cleaned up successfully!")
                except Exception as ce:
                    print(f"[CLEANUP] Notice: Could not delete local folder: {ce}")
        
        # Actionable tips & Pinned Comment Recommendation
        print("\nNext steps for growth and monetization:")
        print("1. RECOMMENDED PINNED COMMENT (Copy & Paste to YouTube Studio to trigger engagement):")
        if niche_key == "facts":
            print("   👉 \"Which of these facts surprised you the most? Comment below! 👇\"")
        else:
            print("   👉 \"Which lesson do you need most in your life right now? Comment below! 👇\"")
        print("2. Consistency is key! Aim to post 1-2 videos per day for rapid growth.")
    except Exception as e:
        print(f"Pipeline stopped: Video composition failed. {e}")

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
        run_pipeline(args.niche, args.topic, args.whisper_model, auto_upload=args.upload)
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
