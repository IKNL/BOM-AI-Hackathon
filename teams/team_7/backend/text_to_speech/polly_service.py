"""
Amazon Polly text-to-speech service.

Usage:
    from text_to_speech import text_to_speech

    audio_bytes = text_to_speech("Hallo wereld")

Environment variables:
    AWS_REGION          - AWS region (default: eu-west-1)
    POLLY_VOICE_ID      - Polly voice (default: Laura, Dutch neural)
    POLLY_OUTPUT_FORMAT - Audio format (default: mp3)
    POLLY_ENGINE        - Engine type: neural or standard (default: neural)

AWS credentials must be configured via environment variables,
~/.aws/credentials, or an IAM role.
"""

import boto3

from .config import AWS_REGION, POLLY_ENGINE, POLLY_OUTPUT_FORMAT, POLLY_VOICE_ID


def text_to_speech(text: str) -> bytes:
    """Convert text to speech audio bytes using Amazon Polly.

    Args:
        text: The text to synthesize.

    Returns:
        Raw audio bytes in the configured output format (default: mp3).

    Raises:
        ValueError: If the input text is empty.
        RuntimeError: If Polly returns no audio stream.
    """
    if not text.strip():
        raise ValueError("Input text is empty.")

    client = boto3.client("polly", region_name=AWS_REGION)

    response = client.synthesize_speech(
        Text=text,
        OutputFormat=POLLY_OUTPUT_FORMAT,
        VoiceId=POLLY_VOICE_ID,
        Engine=POLLY_ENGINE,
    )

    audio_stream = response.get("AudioStream")
    if not audio_stream:
        raise RuntimeError("Polly returned no audio stream.")

    return audio_stream.read()
