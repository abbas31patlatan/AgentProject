# File: perception/audio.py

"""Audio input utilities for speech recognition."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from typing import Optional

import sounddevice as sd


@dataclass
class Recording:
    """Container for recorded audio data."""

    data: bytes
    sample_rate: int


class AudioRecorder:
    """Record raw audio from the default microphone."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def record(self, seconds: int = 1) -> Recording:
        """Record audio for the specified duration."""

        frames = sd.rec(int(seconds * self.sample_rate), samplerate=self.sample_rate, channels=1)
        sd.wait()
        data = frames.astype("int16").tobytes()
        return Recording(data=data, sample_rate=self.sample_rate)

    @staticmethod
    def to_wav(recording: Recording) -> bytes:
        """Convert a recording to WAV bytes."""

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(recording.sample_rate)
            wf.writeframes(recording.data)
        return buf.getvalue()

