"""Interactive voice conversation loop.

Listen → Transcribe (Whisper) → Bedrock LLM → Speak (Polly) → Repeat
"""

import asyncio

from audio import play_mp3, record_until_enter
from llm import chat_with_llm
from speech_to_text import transcribe
from text_to_speech import text_to_speech


def get_response(user_text: str) -> str:
    """Send user text to Bedrock and return the answer."""
    result = asyncio.run(chat_with_llm(user_text))
    return result["answer"]


def main():
    print("=== Voice Conversation ===")
    print("Speak into your microphone, press Enter when done.")
    print("Press Ctrl+C to exit.\n")

    while True:
        try:
            print("You:")
            audio = record_until_enter()

            if audio.size == 0:
                print("  (no audio captured)\n")
                continue

            print("  [Transcribing...]")
            user_text = transcribe(audio)

            if not user_text:
                print("  (nothing detected)\n")
                continue

            print(f"  \"{user_text}\"\n")

            print("  [Thinking...]")
            response = get_response(user_text)
            print(f"Bot: \"{response}\"")

            print("  [Speaking...]")
            mp3_bytes = text_to_speech(response)
            play_mp3(mp3_bytes)
            print()

        except KeyboardInterrupt:
            print("\n\nTot ziens!")
            break


if __name__ == "__main__":
    main()
