# File: media/video_gen.py

"""Utilities for generating simple videos from image frames."""

from __future__ import annotations

import cv2
from typing import Iterable


class VideoGenerator:
    """Create a video from a sequence of images."""

    def __init__(self, fps: int = 24) -> None:
        self.fps = fps

    def generate(self, frames: Iterable[str], out_path: str) -> str:
        """Create a video file from a list of image file paths."""

        first = cv2.imread(next(iter(frames)))
        height, width, _ = first.shape
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (width, height))
        writer.write(first)
        for frame_path in frames:
            img = cv2.imread(frame_path)
            writer.write(img)
        writer.release()
        return out_path

