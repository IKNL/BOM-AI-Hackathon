"""Microphone input via PulseAudio (parecord).

Uses the parecord CLI tool which works reliably on WSL2 via WSLg's
PulseAudio socket.
"""

import subprocess
import struct
import threading

import numpy as np

SAMPLE_RATE = 16000
CHANNELS = 1


def record_until_enter(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Record from the microphone until the user presses Enter.

    Returns:
        NumPy array of float32 audio samples (mono).
    """
    process = subprocess.Popen(
        [
            "parecord",
            "--format=s16le",
            "--rate", str(sample_rate),
            "--channels", str(CHANNELS),
            "--raw",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    chunks: list[bytes] = []
    stop = threading.Event()

    def _read_audio():
        while not stop.is_set():
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            chunks.append(chunk)

    def _wait_for_enter():
        input()
        stop.set()

    reader = threading.Thread(target=_read_audio, daemon=True)
    listener = threading.Thread(target=_wait_for_enter, daemon=True)
    reader.start()
    listener.start()

    print("  [Recording... press Enter to stop]")
    stop.wait()
    process.terminate()
    process.wait()
    reader.join(timeout=2)

    raw = b"".join(chunks)
    if not raw:
        return np.array([], dtype=np.float32)

    samples = struct.unpack(f"<{len(raw) // 2}h", raw)

    return np.array(samples, dtype=np.float32) / 32768.0


def record(duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Record a fixed duration from the microphone.

    Args:
        duration: Recording length in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        NumPy array of float32 audio samples (mono).
    """
    result = subprocess.run(
        [
            "parecord",
            "--format=s16le",
            "--rate", str(sample_rate),
            "--channels", str(CHANNELS),
            "--raw",
            f"--process-time-msec={int(duration * 1000)}",
        ],
        capture_output=True,
        timeout=duration + 2,
    )

    raw = result.stdout
    if not raw:
        return np.array([], dtype=np.float32)

    samples = struct.unpack(f"<{len(raw) // 2}h", raw)

    return np.array(samples, dtype=np.float32) / 32768.0
