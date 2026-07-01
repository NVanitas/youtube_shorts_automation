import asyncio
import edge_tts
from pathlib import Path
from config import NICHES

async def generate_voice_async(text, voice, rate, output_path):
    """Asynchronously generates speech using edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def generate_voice(niche_key, text, video_dir, output_filename=None):
    """Synchronous wrapper to generate voiceover audio using edge-tts."""
    if niche_key not in NICHES:
        raise ValueError(f"Niche '{niche_key}' is not configured.")
        
    niche = NICHES[niche_key]
    voice = niche["voice"]
    rate = niche["rate"]
    
    if not output_filename:
        output_filename = f"{niche_key}_voiceover.mp3"
        
    output_path = video_dir / output_filename
    
    print(f"Generating voiceover using edge-tts voice '{voice}' (rate: {rate})...")
    
    try:
        # Run the async function synchronously
        asyncio.run(generate_voice_async(text, voice, rate, str(output_path)))
        print(f"Voiceover saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Failed to generate voiceover: {e}")
        raise e
