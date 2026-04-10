"""Local audio playback using pygame.mixer."""

import io
import time

import pygame


def _ensure_mixer() -> None:
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def play_mp3(mp3_bytes: bytes) -> None:
    """Play MP3 audio bytes through the default output device.

    Args:
        mp3_bytes: Raw MP3 audio bytes (e.g. from Polly).
    """
    _ensure_mixer()
    sound = pygame.mixer.Sound(io.BytesIO(mp3_bytes))
    sound.play()

    while pygame.mixer.get_busy():
        time.sleep(0.05)


def play_mp3_async(mp3_bytes: bytes) -> pygame.mixer.Sound:
    """Start playing MP3 audio without blocking.

    Returns:
        The ``pygame.mixer.Sound`` instance (call ``.stop()`` to cancel).
    """
    _ensure_mixer()
    sound = pygame.mixer.Sound(io.BytesIO(mp3_bytes))
    sound.play()
    return sound


def stop_playback() -> None:
    """Stop all currently playing audio."""
    if pygame.mixer.get_init():
        pygame.mixer.stop()
