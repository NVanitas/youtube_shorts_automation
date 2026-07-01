import wave
import struct
import math
import random

def generate_cinematic_impact(filename, duration=1.5, sample_rate=44100):
    num_samples = int(duration * sample_rate)
    audio = []
    
    # Lowpass filter state
    y = 0.0
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Envelope: Extremely fast attack (0.01s), long decay
        if t < 0.01:
            env = t / 0.01
        else:
            env = math.exp(-4.0 * (t - 0.01)) # exponential decay
            
        x = random.uniform(-1.0, 1.0)
        
        # Lowpass filter cutoff drops sharply
        cutoff = 1000 * math.exp(-8.0 * t) + 40
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * cutoff)
        alpha = dt / (rc + dt)
        
        y = y + alpha * (x - y)
        
        # Sub bass drop (starts at 100Hz, drops to 20Hz rapidly)
        sub_freq = 100 * math.exp(-4.0 * t) + 20
        sub = math.sin(2 * math.pi * sub_freq * t)
        
        # Heavy distortion/clipping on the sub to add grit
        sub = math.tanh(sub * 4.0)
        
        val = (y * 2.5 + sub * 1.5) * env
        
        # Master soft clip
        val = math.tanh(val)
        
        audio.append(val)
    
    # Apply delay reverb for spatial depth
    delay_samples = int(sample_rate * 0.07)  # 70ms first tap
    delay2 = int(delay_samples * 2.3)       # 160ms second tap
    output = list(audio)
    for i in range(delay_samples, len(output)):
        output[i] += output[i - delay_samples] * 0.3
    for i in range(delay2, len(output)):
        output[i] += output[i - delay2] * 0.15
    # Mix 60% dry / 40% wet
    audio = [d * 0.6 + w * 0.4 for d, w in zip(audio, output)]
        
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for sample in audio:
            sample = math.tanh(sample)  # prevent clipping
            int_sample = max(-32768, min(32767, int(sample * 32767)))
            wav_file.writeframesraw(struct.pack('<h', int_sample))

if __name__ == "__main__":
    generate_cinematic_impact("impact_test.wav")
