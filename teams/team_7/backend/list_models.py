import boto3
from dotenv import load_dotenv
from config import settings

load_dotenv()

client = boto3.client(
    "bedrock",
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    aws_session_token=settings.aws_session_token or None,
)

models = client.list_foundation_models()["modelSummaries"]
for m in models:
    print(f"{m['modelId']}  ({m['providerName']})  - {m.get('modelName', '')}")
