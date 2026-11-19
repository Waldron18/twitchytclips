"""
generate_bgm.py
Generates clean, 100% royalty-free background music tracks for ClipForge Local
using pure harmonic synthesis and FFmpeg conversion.
"""
import os
import subprocess
import numpy as np
from scipy.io import wavfile

def generate_tracks():
    music_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "music")
    os.makedirs(music_dir, exist_ok=True)
    sample_rate = 44100
    duration = 60.0  # 60 seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Track 1: Lo-Fi Chill Beats
    # Chord progression: Cmaj7 - Am7 - Dm7 - G7 (smooth mellow chords with soft bass and vinyl warmth)
    chord_freqs = [
        [261.63, 329.63, 392.00, 493.88],  # Cmaj7
        [220.00, 261.63, 329.63, 392.00],  # Am7
        [293.66, 349.23, 440.00, 523.25],  # Dm7
        [196.00, 246.94, 293.66, 349.23],  # G7
    ]
    chord_duration = 3.75  # seconds per chord (16 bars per cycle)
    lofi_audio = np.zeros_like(t)

    # Sub-bass
    bass_freqs = [65.41, 55.00, 73.42, 49.00]

    for i in range(int(duration / chord_duration)):
        idx = i % len(chord_freqs)
        start_sample = int(i * chord_duration * sample_rate)
        end_sample = min(int((i + 1) * chord_duration * sample_rate), len(t))
        t_segment = t[start_sample:end_sample] - t[start_sample]

        # Chord synth with soft envelope
        segment_signal = np.zeros_like(t_segment)
        for f in chord_freqs[idx]:
            # fundamental + soft overtone
            segment_signal += 0.08 * np.sin(2 * np.pi * f * t_segment)
            segment_signal += 0.02 * np.sin(4 * np.pi * f * t_segment)

        # Smooth attack & release
        env = np.ones_like(t_segment)
        attack = int(0.15 * sample_rate)
        decay = int(0.2 * sample_rate)
        if len(env) > attack + decay:
            env[:attack] = np.linspace(0, 1, attack)
            env[-decay:] = np.linspace(1, 0.4, decay)
        segment_signal *= env

        # Add bass
        f_bass = bass_freqs[idx]
        segment_signal += 0.12 * np.sin(2 * np.pi * f_bass * t_segment)

        lofi_audio[start_sample:end_sample] += segment_signal

    # Add gentle percussion rhythm (soft kick & snare click every beat)
    bpm = 80
    beat_interval = 60.0 / bpm
    total_beats = int(duration / beat_interval)
    for b in range(total_beats):
        beat_start = int(b * beat_interval * sample_rate)
        if b % 2 == 0:
            # Soft kick
            k_len = int(0.08 * sample_rate)
            if beat_start + k_len < len(lofi_audio):
                k_t = np.linspace(0, 0.08, k_len)
                kick = 0.15 * np.sin(2 * np.pi * np.linspace(120, 45, k_len) * k_t) * np.exp(-k_t * 30)
                lofi_audio[beat_start:beat_start + k_len] += kick
        else:
            # Soft snap/brush
            s_len = int(0.06 * sample_rate)
            if beat_start + s_len < len(lofi_audio):
                s_t = np.linspace(0, 0.06, s_len)
                snare = 0.04 * (np.random.rand(s_len) * 2 - 1) * np.exp(-s_t * 50)
                lofi_audio[beat_start:beat_start + s_len] += snare

    # Normalize track 1
    lofi_audio = lofi_audio / (np.max(np.abs(lofi_audio)) + 1e-6) * 0.7
    wav_path1 = os.path.join(music_dir, "lofi_chill.wav")
    mp3_path1 = os.path.join(music_dir, "lofi_chill.mp3")
    wavfile.write(wav_path1, sample_rate, (lofi_audio * 32767).astype(np.int16))

    # Convert to MP3 using ffmpeg
    subprocess.run(["ffmpeg", "-y", "-i", wav_path1, "-c:a", "libmp3lame", "-b:a", "192k", mp3_path1],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(wav_path1):
        os.remove(wav_path1)

    # Track 2: Upbeat Energetic Synth
    upbeat_audio = np.zeros_like(t)
    bpm_fast = 124
    step_interval = 60.0 / bpm_fast / 2.0  # 8th notes
    steps = int(duration / step_interval)
    arp_notes = [440.0, 523.25, 659.25, 783.99, 880.0, 783.99, 659.25, 523.25]

    for s in range(steps):
        s_start = int(s * step_interval * sample_rate)
        note_len = int(step_interval * 0.8 * sample_rate)
        if s_start + note_len < len(upbeat_audio):
            freq = arp_notes[s % len(arp_notes)]
            st = np.linspace(0, step_interval * 0.8, note_len)
            note = 0.07 * np.sin(2 * np.pi * freq * st) * np.exp(-st * 12)
            upbeat_audio[s_start:s_start + note_len] += note

        # Four on the floor kick
        if s % 2 == 0:
            k_len = int(0.1 * sample_rate)
            if s_start + k_len < len(upbeat_audio):
                kt = np.linspace(0, 0.1, k_len)
                kick = 0.22 * np.sin(2 * np.pi * np.linspace(150, 40, k_len) * kt) * np.exp(-kt * 25)
                upbeat_audio[s_start:s_start + k_len] += kick

    upbeat_audio = upbeat_audio / (np.max(np.abs(upbeat_audio)) + 1e-6) * 0.7
    wav_path2 = os.path.join(music_dir, "upbeat_hype.wav")
    mp3_path2 = os.path.join(music_dir, "upbeat_hype.mp3")
    wavfile.write(wav_path2, sample_rate, (upbeat_audio * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-i", wav_path2, "-c:a", "libmp3lame", "-b:a", "192k", mp3_path2],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(wav_path2):
        os.remove(wav_path2)

    print(f"Generated BGM tracks in {music_dir}:")
    print(f" - {mp3_path1} ({os.path.getsize(mp3_path1)} bytes)")
    print(f" - {mp3_path2} ({os.path.getsize(mp3_path2)} bytes)")

if __name__ == "__main__":
    generate_tracks()
