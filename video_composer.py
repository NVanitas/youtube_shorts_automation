import os
import subprocess
from pathlib import Path
import static_ffmpeg

# Initialize static-ffmpeg to guarantee ffmpeg is in PATH
static_ffmpeg.add_paths()

from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips, CompositeVideoClip, VideoClip
from moviepy.video.fx import Loop
from moviepy.audio.fx import AudioLoop
from config import BASE_DIR

def compose_video(niche_key, bg_assets, voiceover_path, bg_music_path, subtitles_ass_path, video_dir):
    """Combines multiple background assets, voiceover, music, and burns subtitles into the final video."""
    print("Initializing video composition...")
    
    # Paths for intermediate and final outputs
    temp_video_path = video_dir / f"{niche_key}_no_subs.mp4"
    final_video_path = video_dir / f"{niche_key}_shorts_final.mp4"
    
    # Load audio clips
    voiceover_audio = AudioFileClip(str(voiceover_path))
    bg_music_audio = AudioFileClip(str(bg_music_path))
    
    # Load transition SFX library (4 variants for variety)
    transition_sounds_dir = BASE_DIR / "assets"
    transition_variants = ["whoosh_riser", "whoosh_swipe", "whoosh_downer", "whoosh_deep"]
    loaded_transitions = []
    for variant in transition_variants:
        p = transition_sounds_dir / f"{variant}.wav"
        if p.exists():
            loaded_transitions.append(AudioFileClip(str(p)).with_volume_scaled(0.04))
    has_transitions = len(loaded_transitions) > 0
    
    # Fallback: old single whoosh
    whoosh_path = BASE_DIR / "assets" / "whoosh.wav"
    has_whoosh = whoosh_path.exists() and not has_transitions
    if has_whoosh:
        whoosh_audio = AudioFileClip(str(whoosh_path)).with_volume_scaled(0.4)
        
    impact_path = BASE_DIR / "assets" / "impact.wav"
    has_impact = impact_path.exists()
    if has_impact:
        impact_audio = AudioFileClip(str(impact_path)).with_volume_scaled(0.7)
    
    duration = voiceover_audio.duration
    print(f"Voiceover duration: {duration:.2f} seconds")
    
    # CTA Logic: Parse ASS file to find the timestamp of "subscribe" or "like"
    cta_time = None
    try:
        with open(subtitles_ass_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) == 10:
                        text = parts[9].lower()
                        if "subscribe" in text or "like" in text or "channel" in text:
                            time_str = parts[1].strip()
                            h, m, s = time_str.split(":")
                            s, cs = s.split(".")
                            cta_time = int(h)*3600 + int(m)*60 + int(s) + int(cs)/100.0
                            print(f"Detected CTA keyword at {time_str} ({cta_time}s)")
                            break
    except Exception as e:
        print(f"Error parsing ASS for CTA: {e}")
        
    bell_path = BASE_DIR / "assets" / "bell.wav"
    click_path = BASE_DIR / "assets" / "click.wav"
    sub_img_path = BASE_DIR / "assets" / "subscribe.png"
    like_img_path = BASE_DIR / "assets" / "like.png"
    bell_icon_path = BASE_DIR / "assets" / "bell_icon.png"
    
    has_cta = (bell_path.exists() and sub_img_path.exists() and 
               like_img_path.exists() and click_path.exists() and bell_icon_path.exists())
    
    # Calculate duration for each individual scene clip
    num_assets = len(bg_assets)
    duration_per_clip = 3.0
    
    import math
    num_scenes = math.ceil(duration / duration_per_clip)
    print(f"Splitting background into {num_scenes} scenes, each playing for ~{duration_per_clip:.2f} seconds.")
    
    processed_clips = []
    
    for i in range(num_scenes):
        idx = i % num_assets
        asset_path = Path(bg_assets[idx])
        
        # Last clip might be shorter to exactly match voiceover duration
        current_clip_duration = duration_per_clip if (i < num_scenes - 1) else (duration - (i * duration_per_clip))
        print(f"Processing scene {i+1}/{num_scenes}: {asset_path.name} (duration: {current_clip_duration:.2f}s)")
        
        # Calculate max zoom out multiplier so it doesn't go below 1.0
        # If duration is 3s, 0.05 * 3 = 0.15. Start at 1.15, go down to 1.0.
        zoom_factor = 0.05 * current_clip_duration
        
        # CASE 1: Asset is an Image (JPG, PNG, WEBP)
        if asset_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            clip = ImageClip(str(asset_path))
            clip = clip.with_duration(current_clip_duration)
            
            # Crop image to vertical 9:16 aspect ratio from center without stretching
            w, h = clip.size
            aspect_ratio = w / h
            target_ratio = 9 / 16
            
            if aspect_ratio > target_ratio:
                # Image is landscape / too wide: scale height to 1920 and crop width
                new_w = int(1920 * aspect_ratio)
                clip = clip.resized(height=1920)
                x1 = (new_w - 1080) // 2
                clip = clip.cropped(x1=x1, y1=0, x2=x1+1080, y2=1920)
            else:
                # Image is too tall: scale width to 1080 and crop height
                new_h = int(1080 / aspect_ratio)
                clip = clip.resized(width=1080)
                y1 = (new_h - 1920) // 2
                clip = clip.cropped(x1=0, y1=y1, x2=1080, y2=y1+1920)
                
            # Double check size is exactly 1080x1920
            clip = clip.resized((1080, 1920))
            
            # Add dynamic smooth zoom & pan effect (Ken Burns) using a custom frame transformation
            def zoom_frame(get_frame, t, i_val=i, zf=zoom_factor, clip_dur=current_clip_duration):
                from PIL import Image
                import numpy as np
                frame = get_frame(t)
                img = Image.fromarray(frame)
                
                # Determine zoom direction (zoom in or out)
                if i_val % 2 == 0:
                    factor = 1.0 / (1.0 + (0.05 * t))
                else:
                    factor = 1.0 / (1.0 + zf - (0.05 * t))
                    
                # Snap Zoom effect: instant 15% zoom halfway through the scene for high energy
                apply_snap = (i_val % 3 == 0 and i_val > 0)
                is_snapping = False
                if apply_snap and t > clip_dur * 0.5:
                    factor *= 0.85
                    if t - (clip_dur * 0.5) < 0.15: # First 150ms of snap
                        is_snapping = True
                    
                crop_w = int(1080 * factor)
                crop_h = int(1920 * factor)
                
                max_offset_x = (1080 - crop_w)
                max_offset_y = (1920 - crop_h)
                
                progress = t / clip_dur
                pan_dir = i_val % 4
                
                if pan_dir == 0:
                    x1 = int(max_offset_x * progress)
                    y1 = int(max_offset_y * progress)
                elif pan_dir == 1:
                    x1 = int(max_offset_x * (1 - progress))
                    y1 = int(max_offset_y * (1 - progress))
                elif pan_dir == 2:
                    x1 = max_offset_x // 2
                    y1 = int(max_offset_y * progress)
                else:
                    x1 = max_offset_x // 2
                    y1 = int(max_offset_y * (1 - progress))
                
                # Crop and resize back to exactly 1080x1920
                cropped = img.crop((x1, y1, x1 + crop_w, y1 + crop_h))
                resized = cropped.resize((1080, 1920), Image.Resampling.BILINEAR)
                
                arr = np.array(resized)
                
                # Chromatic Aberration (Glitch) during Snap Zoom
                if is_snapping:
                    shift = 15
                    # Shift Red channel right
                    arr[:, shift:, 0] = arr[:, :-shift, 0]
                    # Shift Blue channel left
                    arr[:, :-shift, 2] = arr[:, shift:, 2]
                    
                return arr
                
            clip = clip.transform(zoom_frame)
            
            processed_clips.append(clip)
            
        # CASE 2: Asset is a Video or GIF
        elif asset_path.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv", ".gif"]:
            clip = VideoFileClip(str(asset_path))
            
            # Crop video to vertical 9:16 aspect ratio from center
            w, h = clip.size
            target_w = int(h * 9 / 16)
            if w != target_w:
                x1 = (w - target_w) // 2
                x2 = x1 + target_w
                clip = clip.cropped(x1=x1, y1=0, x2=x2, y2=h)
            clip = clip.resized((1080, 1920))
            
            # Adjust video length to match the scene duration
            if clip.duration < current_clip_duration:
                clip = clip.with_effects([Loop(duration=current_clip_duration)])
            else:
                clip = clip.subclipped(0, current_clip_duration)
                
            processed_clips.append(clip)
            


    # Concatenate all scenes into the final background slideshow
    # Clean cuts + our 4-variant transition SFX library is the professional standard for Shorts
    print("Concatenating scenes...")
    video_clip = concatenate_videoclips(processed_clips, method="compose")
    
    # VIRAL EDIT: Apply cinematic film grain texture, vignette, particles, and light leaks
    grain_path = BASE_DIR / "assets" / "grain.png"
    vignette_path = BASE_DIR / "assets" / "vignette.png"
    particles_path = BASE_DIR / "assets" / "particles.png"
    light_leak_path = BASE_DIR / "assets" / "light_leak.png"
    
    if vignette_path.exists() or grain_path.exists() or particles_path.exists():
        print("Applying cinematic overlays (grain/vignette/particles/leaks)...")
        from PIL import Image, ImageDraw, ImageEnhance
        import numpy as np
        
        # Prepare combined static overlay (grain + vignette)
        _combined_overlay = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        
        if vignette_path.exists():
            _vig = Image.open(str(vignette_path)).convert("RGBA")
            _combined_overlay.alpha_composite(_vig)
            
        if grain_path.exists():
            _grain_img = Image.open(str(grain_path)).convert("RGBA")
            _grain_img.putalpha(int(255 * 0.12)) # 12% opacity
            _combined_overlay.alpha_composite(_grain_img)
            
        # Load animated overlays
        _particles_img = None
        if particles_path.exists():
            _particles_img = Image.open(str(particles_path)).convert("RGBA")
            
        _light_leak_img = None
        if light_leak_path.exists():
            _light_leak_img = Image.open(str(light_leak_path)).convert("RGBA")
        
        # We also draw the Progress Bar here for maximum efficiency
        bar_height = 12
        
        def apply_overlays(get_frame, t):
            frame = get_frame(t)
            base_img = Image.fromarray(frame).convert("RGBA")
            
            # 1. Apply Particles (scrolling up based on global time t)
            if _particles_img:
                # scroll speed: 1920 pixels over the whole video duration
                scroll_y = int((t / duration) * 1920)
                # Crop a 1080x1920 window from the 1080x3840 particle image
                particles_frame = _particles_img.crop((0, scroll_y, 1080, scroll_y + 1920))
                base_img.alpha_composite(particles_frame)
                
            # 2. Apply Static Overlays (Grain + Vignette)
            base_img.alpha_composite(_combined_overlay)
            
            # 3. Apply Light Leak Flashes during Scene Transitions
            # Trigger a flash in the last 0.2s of any scene (except the very end of the video)
            scene_t = t % duration_per_clip
            if _light_leak_img and scene_t > duration_per_clip - 0.2 and t < duration - 0.5:
                # fade in opacity from 0 to 1 over the 0.2s window
                leak_alpha = (scene_t - (duration_per_clip - 0.2)) / 0.2
                # Use ImageEnhance to adjust opacity
                enhancer = ImageEnhance.Brightness(_light_leak_img.split()[3]) # Get alpha channel
                mask = enhancer.enhance(leak_alpha)
                leak_frame = _light_leak_img.copy()
                leak_frame.putalpha(mask)
                base_img.alpha_composite(leak_frame)
            
            # 4. Draw Progress Bar
            draw = ImageDraw.Draw(base_img)
            y_pos = 1920 - bar_height
            draw.rectangle([0, y_pos, 1080, 1920], fill=(255, 255, 255, 60))
            progress_w = int(1080 * (t / duration))
            draw.rectangle([0, y_pos, progress_w, 1920], fill=(255, 215, 0, 255)) # Gold color
            
            return np.array(base_img.convert("RGB"))
            
        video_clip = video_clip.transform(apply_overlays)
    
    # Process background music (Loop or Cut)
    # VIRAL EDIT: Cut background music 3.5 seconds before the end for dramatic silence hook
    cut_time = max(0, duration - 3.5)
    
    if bg_music_audio.duration < cut_time:
        bg_music_audio = bg_music_audio.with_effects([AudioLoop(duration=cut_time)])
    else:
        bg_music_audio = bg_music_audio.subclipped(0, cut_time)
        
    music_vol = 0.04 if niche_key == "stoicism" else 0.06
    bg_music_audio = bg_music_audio.with_volume_scaled(music_vol)
    
    audio_tracks = [voiceover_audio, bg_music_audio]
    
    if has_cta and cta_time is not None:
        # Sequential audio: Click -> Click -> Bell
        if cta_time < duration:
            audio_tracks.append(AudioFileClip(str(click_path)).with_volume_scaled(0.8).with_start(cta_time))
        if cta_time + 0.5 < duration:
            audio_tracks.append(AudioFileClip(str(click_path)).with_volume_scaled(0.8).with_start(cta_time + 0.5))
        if cta_time + 1.0 < duration:
            audio_tracks.append(AudioFileClip(str(bell_path)).with_volume_scaled(0.35).with_start(cta_time + 1.0))
    
    if has_impact:
        # Add heavy sub-bass impact at the very beginning to retain attention (Hook)
        audio_tracks.append(impact_audio.with_start(0.0))
    
    if has_whoosh:
        # Fallback: single whoosh at each transition
        for i in range(1, num_scenes):
            transition_time = i * duration_per_clip
            if transition_time < duration:
                audio_tracks.append(whoosh_audio.with_start(transition_time - 0.05))
                
    if has_transitions:
        # Use rotating variants at each transition for maximum variety
        for i in range(1, num_scenes):
            transition_time = i * duration_per_clip
            if transition_time < duration:
                variant = loaded_transitions[i % len(loaded_transitions)]
                # Start slightly before the cut so the audio leads the visual
                audio_tracks.append(variant.with_start(transition_time - 0.08))
    
    # Mix audio tracks (voiceover + background music + whooshes)
    combined_audio = CompositeAudioClip(audio_tracks)
    video_clip = video_clip.with_audio(combined_audio)
    
    # Apply Visual CTA overlays (Animated & Sequential)
    if has_cta and cta_time is not None:
        import math
        
        def ease_out_back(x):
            c1 = 1.70158
            c3 = c1 + 1
            return 1 + c3 * math.pow(x - 1, 3) + c1 * math.pow(x - 1, 2)
            
        def slide_up(t, target_y, duration=0.4, end_t=2.5):
            if t < duration:
                progress = t / duration
                eased = ease_out_back(progress)
                y = 1920 - ((1920 - target_y) * eased)
                return ("center", y)
            elif t > end_t - 0.3:
                dt = (t - (end_t - 0.3)) / 0.3
                y = target_y + ((1920 - target_y) * (dt ** 2))
                return ("center", y)
            return ("center", target_y)
            
        def slide_up_bell(t, target_y, duration=0.4, end_t=1.5):
            if t < duration:
                progress = t / duration
                eased = ease_out_back(progress)
                y = 1920 - ((1920 - target_y) * eased)
                return (860, y) # Shifted right to match wider 600px subscribe button
            elif t > end_t - 0.3:
                dt = (t - (end_t - 0.3)) / 0.3
                y = target_y + ((1920 - target_y) * (dt ** 2))
                return (860, y)
            return (860, target_y)

        # LIKE animates first at t=0
        dur_like = max(0.5, min(2.5, duration - cta_time))
        like_clip = (ImageClip(str(like_img_path))
                     .with_start(cta_time)
                     .with_duration(dur_like)
                     .with_position(lambda t: slide_up(t, 1250, end_t=dur_like)))
        
        cta_layers = [video_clip, like_clip]
        
        # SUBSCRIBE animates at t+0.5 (only if enough time left)
        if cta_time + 0.5 < duration - 0.3:
            dur_sub = max(0.5, min(2.0, duration - (cta_time + 0.5)))
            sub_clip = (ImageClip(str(sub_img_path))
                        .with_start(cta_time + 0.5)
                        .with_duration(dur_sub)
                        .with_position(lambda t: slide_up(t, 1430, end_t=dur_sub)))
            cta_layers.append(sub_clip)
                    
        # BELL animates at t+1.0 (only if enough time left)
        if cta_time + 1.0 < duration - 0.3:
            dur_bell = max(0.5, min(1.5, duration - (cta_time + 1.0)))
            bell_clip = (ImageClip(str(bell_icon_path))
                         .with_start(cta_time + 1.0)
                         .with_duration(dur_bell)
                         .with_position(lambda t: slide_up_bell(t, 1430, end_t=dur_bell)))
            cta_layers.append(bell_clip)
            
        # CTA Text Overlay Banner ("SUB FOR MORE WEIRD FACTS" / "SUB FOR DAILY STOIC WISDOM")
        cta_text_file = BASE_DIR / "assets" / f"cta_text_{niche_key}.png"
        if cta_text_file.exists():
            dur_text = max(0.5, min(3.0, duration - cta_time))
            text_banner_clip = (ImageClip(str(cta_text_file))
                                .with_start(cta_time)
                                .with_duration(dur_text)
                                .with_position(lambda t: slide_up(t, 1100, end_t=dur_text)))
            cta_layers.append(text_banner_clip)
    # Check if cta_layers is defined, if not, create it with video_clip
    try:
        cta_layers
    except NameError:
        cta_layers = [video_clip]
        
    video_clip = CompositeVideoClip(cta_layers)
    
    # NOTE: Flash cut removed — crossfade transitions are now applied above for a
    # smoother, more professional look instead of harsh white flashes.
    
    # Render intermediate video without subtitles
    print("Rendering video with mixed audio (no subtitles)...")
    video_clip.write_videofile(
        str(temp_video_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        bitrate="5M",
        logger=None
    )
    
    # Close clips to release resources
    video_clip.close()
    for c in processed_clips:
        c.close()
    voiceover_audio.close()
    bg_music_audio.close()
    
    # Burn-in subtitles using FFmpeg (fast and doesn't require ImageMagick)
    print("Burning subtitles using FFmpeg...")
    
    # Format path for FFmpeg subtitles filter on Windows
    ass_path_formatted = str(subtitles_ass_path).replace("\\", "/")
    if ":" in ass_path_formatted:
        drive, rest = ass_path_formatted.split(":", 1)
        ass_path_formatted = f"{drive}\\:{rest}"
        
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(temp_video_path),
        "-vf", f"subtitles='{ass_path_formatted}'",
        "-c:v", "libx264",
        "-crf", "16",
        "-preset", "slow",
        "-c:a", "copy",
        str(final_video_path)
    ]
    
    try:
        # Run FFmpeg
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        print(f"Video created successfully! Final file: {final_video_path}")
        
        # Clean up intermediate file
        if temp_video_path.exists():
            temp_video_path.unlink()
            
        return final_video_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed with exit code {e.returncode}")
        print(f"FFmpeg stdout: {e.stdout}")
        print(f"FFmpeg stderr: {e.stderr}")
        raise e
