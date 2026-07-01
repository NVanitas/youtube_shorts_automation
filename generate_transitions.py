"""
Gerador de efeitos sonoros de transição cinematográficos de alta qualidade.
Gera 4 variações de whoosh + 2 tipos de cut sounds para variedade entre as cenas.
"""
import wave
import struct
import math
import random

def _write_wav_stereo(filepath, audio_l, audio_r, sample_rate=44100):
    """Write stereo WAV file from two mono lists."""
    with wave.open(filepath, 'w') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for l, r in zip(audio_l, audio_r):
            l_int = max(-32768, min(32767, int(l * 32767)))
            r_int = max(-32768, min(32767, int(r * 32767)))
            f.writeframesraw(struct.pack('<hh', l_int, r_int))

def _lowpass(audio, cutoff_start, cutoff_end, sample_rate=44100):
    """Apply a time-varying lowpass filter to audio samples."""
    y = 0.0
    out = []
    n = len(audio)
    for i, x in enumerate(audio):
        t_ratio = i / n
        cutoff = cutoff_start + (cutoff_end - cutoff_start) * t_ratio
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * max(cutoff, 20))
        alpha = dt / (rc + dt)
        y = y + alpha * (x - y)
        out.append(y)
    return out

def generate_whoosh_riser(filepath, sample_rate=44100):
    """
    Whoosh tipo RISER: vai de grave para agudo, pan esquerda->direita.
    Efeito de velocidade. Usado em transições rápidas de corte.
    """
    duration = 0.55
    n = int(duration * sample_rate)
    noise = [random.gauss(0, 1) for _ in range(n)]
    
    audio_l, audio_r = [], []
    y = 0.0
    for i in range(n):
        t = i / sample_rate
        progress = t / duration
        
        # Envelope: fast attack, fast decay at end
        if t < 0.05:
            env = t / 0.05
        elif t > duration - 0.1:
            env = 1.0 - (t - (duration - 0.1)) / 0.1
        else:
            env = 1.0
        env = env ** 1.5
        
        # Rising frequency sweep on noise - much softer cutoff
        cutoff = 300 + 1200 * (progress ** 0.7)
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * cutoff)
        alpha = dt / (rc + dt)
        y = y + alpha * (noise[i] - y)
        
        # Add a very faint shimmer
        shimmer = math.sin(2 * math.pi * (2000 + 2000 * progress) * t) * 0.03
        
        val = (y * 1.2 + shimmer) * env
        val = math.tanh(val * 1.2)
        
        # Stereo pan: left-to-right as it rises
        pan = progress
        l = val * math.sqrt(max(0, 1.0 - pan))
        r = val * math.sqrt(pan)
        audio_l.append(l)
        audio_r.append(r)
    
    _write_wav_stereo(filepath, audio_l, audio_r, sample_rate)

def generate_whoosh_downer(filepath, sample_rate=44100):
    """
    Whoosh tipo DOWNER: vai de agudo para grave, pan direita->esquerda.
    Efeito de impacto descendente.
    """
    duration = 0.5
    n = int(duration * sample_rate)
    
    audio_l, audio_r = [], []
    y = 0.0
    for i in range(n):
        t = i / sample_rate
        progress = t / duration
        
        # Envelope: punch attack, slow decay
        if t < 0.02:
            env = t / 0.02
        else:
            env = math.exp(-3.5 * (t - 0.02))
        
        # Falling frequency + white noise (softer)
        x = random.gauss(0, 1)
        cutoff = 1500 - 1200 * (progress ** 0.5)
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * max(cutoff, 80))
        alpha = dt / (rc + dt)
        y = y + alpha * (x - y)
        
        # Sub thud underneath (very light)
        sub = math.sin(2 * math.pi * (100 - 50 * progress) * t) * math.exp(-8 * t) * 0.3
        
        val = (y * 1.0 + sub) * env
        val = math.tanh(val)
        
        # Stereo pan: right-to-left
        pan = 1.0 - progress
        l = val * math.sqrt(max(0, 1.0 - pan))
        r = val * math.sqrt(pan)
        audio_l.append(l)
        audio_r.append(r)
    
    _write_wav_stereo(filepath, audio_l, audio_r, sample_rate)

def generate_whoosh_swipe(filepath, sample_rate=44100):
    """
    Whoosh tipo SWIPE: som de rasgar de tela, curtíssimo e agressivo.
    Ideal para cortes de alta energia.
    """
    duration = 0.35
    n = int(duration * sample_rate)
    
    audio_l, audio_r = [], []
    y = 0.0
    for i in range(n):
        t = i / sample_rate
        progress = t / duration
        
        # Triangular envelope: sharp peak at 20%
        if progress < 0.2:
            env = progress / 0.2
        else:
            env = 1.0 - (progress - 0.2) / 0.8
        env = env ** 1.2
        
        # Very fast frequency sweep (softer)
        x = random.gauss(0, 1)
        cutoff = 400 + 2000 * (progress ** 0.4) * (1.0 - progress)
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * max(cutoff, 50))
        alpha = dt / (rc + dt)
        y = y + alpha * (x - y)
        
        val = y * 1.2 * env
        val = math.tanh(val * 1.5)
        
        # Center pan with slight stereo width
        width = math.sin(math.pi * progress)
        audio_l.append(val * (0.7 + 0.3 * width))
        audio_r.append(val * (0.7 - 0.3 * width + 0.6))
    
    _write_wav_stereo(filepath, audio_l, audio_r, sample_rate)

def generate_whoosh_deep(filepath, sample_rate=44100):
    """
    Whoosh tipo DEEP: sub-bass pesado com ar ao redor. Mais dramático/filosófico.
    Ideal para o nicho Stoicism.
    """
    duration = 0.7
    n = int(duration * sample_rate)
    
    audio_l, audio_r = [], []
    y_hi = 0.0
    y_lo = 0.0
    for i in range(n):
        t = i / sample_rate
        progress = t / duration
        
        # Slow build envelope
        if t < 0.15:
            env = t / 0.15
        elif t > duration - 0.2:
            env = 1.0 - (t - (duration - 0.2)) / 0.2
        else:
            env = 1.0
        env = math.pow(env, 0.6)
        
        x = random.gauss(0, 1)
        
        # High layer (air) - extremely subtle
        rc_hi = 1.0 / (2.0 * math.pi * 800)
        alpha_hi = (1 / sample_rate) / (rc_hi + 1 / sample_rate)
        y_hi = y_hi + alpha_hi * (x - y_hi)
        
        # Low layer (sub) - much softer
        sub_freq = 50 + 10 * math.sin(math.pi * progress)
        sub = math.sin(2 * math.pi * sub_freq * t) * math.exp(-2.5 * t) * 0.4
        
        val = (y_hi * 0.4 + sub * 0.8) * env
        val = math.tanh(val)
        
        # Subtle wide stereo
        noise_spread = random.gauss(0, 0.04)
        audio_l.append(val - noise_spread)
        audio_r.append(val + noise_spread)
    
    _write_wav_stereo(filepath, audio_l, audio_r, sample_rate)

def generate_all_transitions(assets_dir):
    """Generate all 4 transition sound variants."""
    import os
    os.makedirs(assets_dir, exist_ok=True)
    
    print("Generating premium transition SFX library...")
    generate_whoosh_riser(f"{assets_dir}/whoosh_riser.wav")
    generate_whoosh_downer(f"{assets_dir}/whoosh_downer.wav")
    generate_whoosh_swipe(f"{assets_dir}/whoosh_swipe.wav")
    generate_whoosh_deep(f"{assets_dir}/whoosh_deep.wav")
    print("4 transition variants generated: riser, downer, swipe, deep.")

if __name__ == "__main__":
    generate_all_transitions("assets")
