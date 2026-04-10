import boto3
from config import settings

c = boto3.client(
    "bedrock",
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    aws_session_token=settings.aws_session_token,
)
m = c.get_foundation_model(modelIdentifier="openai.gpt-oss-120b-1:0")["modelDetails"]
print(f"Max input tokens: {m.get('inputTokenLimit', 'N/A')}")
print(f"Max output tokens: {m.get('outputTokenLimit', 'N/A')}")
print(f"Streaming: {m.get('responseStreamingSupported')}")
