"""Speech-to-text transcription using openai-whisper."""

import numpy as np
import whisper

from .config import WHISPER_LANGUAGE, WHISPER_MODEL

_model = None


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        print(f"Loading Whisper model '{WHISPER_MODEL}'...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("Model loaded.")
    return _model


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe audio samples to text using Whisper.

    Args:
        audio: NumPy array of float32 audio samples (mono, 16kHz recommended).
        sample_rate: Sample rate of the audio.

    Returns:
        Transcribed text string.
    """
    model = _get_model()

    result = model.transcribe(
        audio,
        language=WHISPER_LANGUAGE,
        fp16=False,
    )

    return result["text"].strip()
