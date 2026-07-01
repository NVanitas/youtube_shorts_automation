import wave, struct, math, random

def generate_cinematic_whoosh(filename, duration=0.6, sample_rate=44100):
    num_samples = int(duration * sample_rate)
    audio = []
    y = 0.0
    for i in range(num_samples):
        t = i / sample_rate
        if t < 0.2:
            env = t / 0.2
        else:
            env = 1.0 - ((t - 0.2) / (duration - 0.2))
        env = env ** 2
        x = random.uniform(-1.0, 1.0)
        cutoff = 1500 - 1400 * (t / duration)
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * cutoff)
        alpha = dt / (rc + dt)
        y = y + alpha * (x - y)
        sub_freq = 80 - 40 * (t / duration)
        sub = math.sin(2 * math.pi * sub_freq * t)
        val = (y * 2.0 + sub * 0.4) * env
        val = max(-1.0, min(1.0, val))
        audio.append(val)
        
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i, sample in enumerate(audio):
            # Stereo Panning: Left to Right
            pan = i / num_samples
            left_val = sample * math.sqrt(1.0 - pan)
            right_val = sample * math.sqrt(pan)
            
            left_sample = max(-32768, min(32767, int(left_val * 32767)))
            right_sample = max(-32768, min(32767, int(right_val * 32767)))
            wav_file.writeframesraw(struct.pack('<hh', left_sample, right_sample))

if __name__ == "__main__":
    import os
    os.makedirs("assets", exist_ok=True)
    generate_cinematic_whoosh("assets/whoosh.wav")
    print("Whoosh generated successfully.")

