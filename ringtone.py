"""Ringtone generator for Get It daily reminder app.

Port of the original tkinter RingtoneGenerator class.
All 7 ringtone methods produce identical sounds to the original.
"""

import numpy as np
import pygame


class RingtoneGenerator:
    """Modern ringtone generator with 7 distinct sounds."""

    @staticmethod
    def _make_stereo(mono_array: np.ndarray) -> np.ndarray:
        """Convert mono array to stereo."""
        if len(mono_array.shape) == 1:
            return np.column_stack((mono_array, mono_array))
        return mono_array

    @staticmethod
    def create_dingdong() -> pygame.mixer.Sound:
        """Generate an elegant ding-dong chime."""
        duration: float = 1.2
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Harmonious note combination
        freq1: float = 880  # A5
        freq2: float = 660  # E5
        sound1: np.ndarray = 0.6 * np.sin(2 * np.pi * freq1 * t[: int(0.4 * sample_rate)])
        sound2: np.ndarray = 0.6 * np.sin(2 * np.pi * freq2 * t[: int(0.4 * sample_rate)])

        # Add harmonics
        sound1 += 0.2 * np.sin(2 * np.pi * freq1 * 2 * t[: int(0.4 * sample_rate)])
        sound2 += 0.2 * np.sin(2 * np.pi * freq2 * 2 * t[: int(0.4 * sample_rate)])

        audio: np.ndarray = np.zeros(samples)
        audio[0 : len(sound1)] = sound1
        audio[int(0.5 * sample_rate) : int(0.5 * sample_rate) + len(sound2)] = sound2

        # Smoother envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.1 * sample_rate)
        decay: int = int(0.3 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + decay] = np.exp(-3 * (t[attack : attack + decay] - 0.1))
        envelope[attack + decay :] = np.exp(-8 * (t[attack + decay :] - 0.4))

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_chime() -> pygame.mixer.Sound:
        """Generate a pleasant wind chime sound."""
        duration: float = 2.5
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Wind chime note sequence
        frequencies: list[float] = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        amplitudes: list[float] = [0.5, 0.4, 0.3, 0.2]
        audio: np.ndarray = np.zeros(samples)

        for i, (freq, amp) in enumerate(zip(frequencies, amplitudes)):
            start: float = i * 0.3
            if start < duration:
                freq_duration: float = duration - start
                freq_samples: int = int(freq_duration * sample_rate)
                freq_t: np.ndarray = np.linspace(0, freq_duration, freq_samples, False)

                # Bell-like characteristics
                freq_audio: np.ndarray = amp * (
                    np.sin(2 * np.pi * freq * freq_t)
                    + 0.3 * np.sin(2 * np.pi * freq * 2 * freq_t)
                    + 0.1 * np.sin(2 * np.pi * freq * 3 * freq_t)
                )

                # Exponential decay envelope
                freq_envelope: np.ndarray = np.exp(-1.5 * freq_t)
                freq_audio = freq_audio * freq_envelope

                start_sample: int = int(start * sample_rate)
                end_sample: int = start_sample + len(freq_audio)
                if end_sample <= samples:
                    audio[start_sample:end_sample] += freq_audio

        audio = (audio * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_beep() -> pygame.mixer.Sound:
        """Generate a modern beep sound."""
        duration: float = 0.6
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Frequency modulation for modern feel
        base_freq: float = 1200
        mod_freq: float = 8
        mod_depth: float = 100
        freq: np.ndarray = base_freq + mod_depth * np.sin(2 * np.pi * mod_freq * t)

        # Square wave mixed with sine wave
        square_wave: np.ndarray = 0.5 * np.sign(np.sin(2 * np.pi * freq * t))
        sine_wave: np.ndarray = 0.3 * np.sin(2 * np.pi * freq * t)
        audio: np.ndarray = 0.7 * square_wave + 0.3 * sine_wave

        # Carefully designed envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.05 * sample_rate)
        sustain: int = int(0.4 * sample_rate)
        release: int = int(0.15 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + sustain] = 0.8
        envelope[attack + sustain :] = np.linspace(0.8, 0, release)

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_alert() -> pygame.mixer.Sound:
        """Generate a professional alert sound."""
        duration: float = 1.2
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Alternating frequencies for urgency
        freq_high: float = 1600
        freq_low: float = 1000
        switch_rate: int = 6
        audio: np.ndarray = np.zeros(samples)

        for i in range(int(duration * switch_rate)):
            start_sample: int = int(i * sample_rate / switch_rate)
            end_sample: int = int((i + 0.5) * sample_rate / switch_rate)

            if i % 2 == 0:
                # High-frequency part with harmonics
                segment: np.ndarray = 0.5 * (
                    np.sin(2 * np.pi * freq_high * t[start_sample:end_sample])
                    + 0.2 * np.sin(2 * np.pi * freq_high * 2 * t[start_sample:end_sample])
                )
            else:
                segment = 0.5 * np.sin(2 * np.pi * freq_low * t[start_sample:end_sample])

            if end_sample <= samples:
                audio[start_sample:end_sample] = segment

        # Dynamic envelope
        envelope: np.ndarray = np.exp(-1.2 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 2 * t))

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_notification() -> pygame.mixer.Sound:
        """Generate a modern notification sound."""
        duration: float = 0.8
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Rising frequency for positive feel
        start_freq: float = 800
        end_freq: float = 1200
        freq: np.ndarray = np.linspace(start_freq, end_freq, samples)

        audio: np.ndarray = 0.7 * np.sin(2 * np.pi * freq * t)

        # Fast attack, slow release envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.1 * sample_rate)
        release_start: int = int(0.3 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[release_start:] = np.exp(-3 * (t[release_start:] - 0.3))

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_piano() -> pygame.mixer.Sound:
        """Generate a piano tone."""
        duration: float = 1.5
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Piano harmonics
        frequencies: list[float] = [261.63, 523.25, 784.88, 1046.50]  # C4, C5, G5, C6
        amplitudes: list[float] = [0.7, 0.5, 0.3, 0.2]

        audio: np.ndarray = np.zeros(samples)
        for freq, amp in zip(frequencies, amplitudes):
            # Each harmonic has a different decay rate
            decay_rate: float = 1.0 + 0.5 * (freq / 261.63)
            freq_envelope: np.ndarray = np.exp(-decay_rate * t)
            audio += amp * np.sin(2 * np.pi * freq * t) * freq_envelope

        # Add percussive attack
        attack_env: np.ndarray = np.exp(-15 * t)
        audio = audio * attack_env

        audio = (audio * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_synth() -> pygame.mixer.Sound:
        """Generate a synthesizer tone."""
        duration: float = 1.0
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Multiple oscillators for rich timbre
        freq1: float = 440  # A4
        freq2: float = 554.37  # C#5
        audio: np.ndarray = (
            0.5 * np.sin(2 * np.pi * freq1 * t)
            + 0.3 * np.sin(2 * np.pi * freq2 * t)
            + 0.1 * np.sin(2 * np.pi * freq1 * 2 * t)
            + 0.1 * np.sin(2 * np.pi * freq2 * 2 * t)
        )

        # Low-pass filter effect
        filter_env: np.ndarray = np.exp(-2 * t)
        audio = audio * (0.8 + 0.2 * filter_env)

        # Envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.05 * sample_rate)
        decay: int = int(0.3 * sample_rate)
        sustain: float = 0.7
        release: int = int(0.2 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + decay] = np.linspace(1, sustain, decay)
        envelope[attack + decay : -release] = sustain
        envelope[-release:] = np.linspace(sustain, 0, release)

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)
