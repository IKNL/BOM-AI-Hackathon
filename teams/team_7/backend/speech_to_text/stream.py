"""
Live speech-to-text streaming from microphone.

Usage:
    python -m speech_to_text --stream

Requires: pip install sounddevice numpy
"""

import sys
import threading

import numpy as np
import sounddevice as sd
import whisper

from .config import WHISPER_LANGUAGE, WHISPER_MODEL

SAMPLE_RATE = 16000
BLOCK_DURATION = 0.5  # seconds per block
SILENCE_THRESHOLD = 0.05
SILENCE_BLOCKS = 3  # number of silent blocks before transcribing


def stream():
    print(f"Model '{WHISPER_MODEL}' laden...")
    model = whisper.load_model(WHISPER_MODEL)
    print("Luisteren... (druk Enter om te stoppen)\n")

    audio_buffer = []
    silent_count = 0
    speaking = False
    running = True

    def wait_for_enter():
        nonlocal running
        input()
        running = False

    threading.Thread(target=wait_for_enter, daemon=True).start()

    def callback(indata, frames, time_info, status):
        nonlocal silent_count, speaking

        block = indata[:, 0].copy()
        level = np.abs(block).max()

        if level >= SILENCE_THRESHOLD:
            speaking = True
            silent_count = 0
            audio_buffer.append(block)
        elif speaking:
            silent_count += 1
            audio_buffer.append(block)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=int(BLOCK_DURATION * SAMPLE_RATE),
        callback=callback,
    ):
        while running:
            sd.sleep(100)

            if speaking and silent_count >= SILENCE_BLOCKS and audio_buffer:
                audio_np = np.concatenate(audio_buffer)
                audio_buffer.clear()
                speaking = False
                silent_count = 0

                result = model.transcribe(
                    audio_np, language=WHISPER_LANGUAGE, fp16=False
                )
                text = result["text"].strip()
                if text:
                    print(text)

    print("Gestopt.")
