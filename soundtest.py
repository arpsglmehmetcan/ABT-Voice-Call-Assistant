import numpy as np
import soundfile as sf

# 3 saniyelik test sesi oluştur
sample_rate = 16000
duration = 3
t = np.linspace(0, duration, int(sample_rate * duration))
audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440 Hz ton

sf.write('test_audio.wav', audio, sample_rate)