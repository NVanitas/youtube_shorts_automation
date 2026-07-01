import re
from pathlib import Path
import stable_whisper
from config import NICHES, ASS_STYLE_TEMPLATE

def rgb_to_bgr(rgb_hex):
    """Converts a standard RGB hex color string (e.g., 'D4AF37') to ASS BGR format ('37AFD4')."""
    rgb_hex = rgb_hex.strip().replace("#", "")
    if len(rgb_hex) != 6:
        return "FFFFFF"  # Fallback to white
    r, g, b = rgb_hex[0:2], rgb_hex[2:4], rgb_hex[4:6]
    return f"{b}{g}{r}"

def apply_custom_style(ass_path, niche_key):
    """Parses the generated ASS file and replaces the default style with our custom niche style."""
    niche = NICHES[niche_key]
    
    # Convert RGB colors from config to BGR format for ASS
    primary_bgr = rgb_to_bgr(niche["primary_color"])
    highlight_bgr = rgb_to_bgr(niche["highlight_color"])
    outline_bgr = rgb_to_bgr(niche["outline_color"])
    
    # Format the style template
    custom_style = ASS_STYLE_TEMPLATE.format(
        font_name=niche["font_name"],
        font_size=niche["font_size"],
        primary_colour=primary_bgr,
        highlight_colour=highlight_bgr,
        outline_colour=outline_bgr,
        alignment=niche["alignment"],
        margin_v=niche["margin_v"]
    )
    
    with open(ass_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # We replace everything from [V4+ Styles] to [Events] with our custom header style
    # The default generated header of stable-ts has:
    # [V4+ Styles]
    # Format: ...
    # Style: Default,...
    
    # Find the [Events] section which marks the start of dialogue
    events_idx = content.find("[Events]")
    if events_idx == -1:
        print("Warning: [Events] section not found in ASS file. Subtitle styling might be default.")
        return
        
    dialogue_section = content[events_idx:]
    
    # Rebuild the ASS file
    new_content = custom_style + "\n" + dialogue_section
    
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Applied custom style '{niche['font_name']}' to: {ass_path}")

def animate_ass_subtitles(ass_path):
    """Injects a pop-in animation tag to every dialogue line to create the Hormozi bounce effect."""
    with open(ass_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # 3-Stage Spring Bounce: 135% over 60ms, dip to 95% over 80ms, settle at 100% over 80ms
    pop_tag = "{\\t(0,60,\\fscx135\\fscy135)\\t(60,140,\\fscx95\\fscy95)\\t(140,220,\\fscx100\\fscy100)}"
    
    new_lines = []
    for line in lines:
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) == 10:
                parts[9] = pop_tag + parts[9]
                line = ",".join(parts)
        new_lines.append(line)
        
    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Injected pop-in animation to subtitles: {ass_path}")

def highlight_ass_keywords(ass_path, niche_key, keywords=None):
    """Highlights key words and numbers in ASS subtitles with vibrant custom style and color."""
    niche = NICHES[niche_key]
    primary_bgr = rgb_to_bgr(niche["primary_color"])
    highlight_bgr = rgb_to_bgr(niche["highlight_color"])
    
    kw_set = set()
    if keywords:
        for kw in keywords:
            for w in re.findall(r'\w+', str(kw).lower()):
                if len(w) > 2:
                    kw_set.add(w)
                    
    # Add numbers and high-impact vocabulary
    impact_words = {
        "one", "two", "three", "four", "five", "first", "second", "third",
        "brain", "mind", "secret", "power", "death", "truth", "lies", "universe",
        "space", "ocean", "body", "dream", "goals", "success", "peace", "anger",
        "control", "freedom", "overthinking", "silence", "toughness", "terrifying",
        "superpowers", "immortal", "shocking", "unbelievable", "mysterious"
    }
    kw_set.update(impact_words)
    
    with open(ass_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) == 10:
                text = parts[9]
                
                # Check if this dialogue line contains any keyword
                words_in_text = [re.sub(r'[^\w]', '', w).lower() for w in re.findall(r'\b\w+\b', text)]
                has_keyword = any(w.isdigit() or w in kw_set or len(w) >= 7 for w in words_in_text)
                
                if has_keyword:
                    parts[3] = "Highlight"  # Switch ASS Style to Highlight (Yellow/Gold)
                    
                def repl(m):
                    ktag = m.group(1) if m.group(1) else ""
                    w = m.group(2)
                    clean_w = re.sub(r'[^\w]', '', w).lower()
                    if clean_w.isdigit() or clean_w in kw_set or len(clean_w) >= 7:
                        return f"{ktag}{{\\c&H00{highlight_bgr}&}}{w.upper()}{{\\c&H00{primary_bgr}&}}"
                    return f"{ktag}{w}"
                    
                # Match optional karaoke tag and word
                new_text = re.sub(r'({\\[kK]f?\d+\})?([^\s{}]+)', repl, text)
                parts[9] = new_text
                line = ",".join(parts)
        new_lines.append(line)
        
    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Highlighted key words and applied Highlight style in subtitles: {ass_path}")

def generate_subtitles(niche_key, audio_path, video_dir, keywords=None, model_name="base"):
    """Transcribes audio and generates a styled ASS subtitle file using stable-ts."""
    if niche_key not in NICHES:
        raise ValueError(f"Niche '{niche_key}' is not configured.")
        
    print(f"Loading Whisper model '{model_name}' and transcribing voiceover...")
    
    try:
        # Load stable-whisper model
        model = stable_whisper.load_model(model_name)
        
        # Transcribe the audio file
        result = model.transcribe(str(audio_path), language="en")
        
        # Split into short, punchy 2-3 word segments for viral pacing
        result.split_by_length(max_words=2)
        
        # Output ASS path
        ass_filename = f"{niche_key}_subtitles.ass"
        ass_path = video_dir / ass_filename
        
        # Export to ASS with karaoke enabled (word-by-word progressive filling highlight)
        result.to_ass(str(ass_path), karaoke=True, word_level=True, segment_level=False)
        print(f"Subtitles generated successfully at: {ass_path}")
        
        # Style the subtitles
        apply_custom_style(ass_path, niche_key)
        
        # Highlight keywords
        highlight_ass_keywords(ass_path, niche_key, keywords)
        
        # Add pop-in animations
        animate_ass_subtitles(ass_path)
        
        return ass_path
    except Exception as e:
        print(f"Failed to generate subtitles: {e}")
        raise e

