import os

AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
POLLY_VOICE_ID = os.environ.get("POLLY_VOICE_ID", "Laura")
POLLY_OUTPUT_FORMAT = os.environ.get("POLLY_OUTPUT_FORMAT", "mp3")
POLLY_ENGINE = os.environ.get("POLLY_ENGINE", "neural")
