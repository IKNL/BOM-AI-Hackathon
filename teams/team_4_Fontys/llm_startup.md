# LLM Startup Guide

## Quick Start

```bash
python3 bedrock_query.py
```

## Model: OpenAI GPT-OSS 120B

- **Parameters**: 120 billion
- **Use Cases**: Medical support, cancer assistance, complex reasoning
- **Region**: us-east-1 (AWS Bedrock)
- **Auth**: EC2 IAM role (automatic)
- **RAG Ready**: Yes, can integrate document retrieval

## Usage

1. Run the script
2. Type your question at the `You:` prompt
3. Press Enter
4. Get response from the LLM
5. Type `exit`, `quit`, or `bye` to stop

## Code

```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

# OpenAI GPT-OSS 120B - Non-Chinese, works reliably
model_id = "openai.gpt-oss-120b-1:0"

def query(prompt: str) -> str:
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "temperature": 0.3
        })
    )
    result = json.loads(response['body'].read())
    return result['choices'][0]['message']['content']

if __name__ == "__main__":
    while True:
        prompt = input("\nYou: ").strip()
        if not prompt:
            continue
        if prompt.lower() in ['exit', 'quit', 'bye']:
            break
        print(f"\nAssistant: {query(prompt)}")
    print("\nGoodbye!")
```

## Configuration

Edit `bedrock_query.py` to change:
- `max_tokens` - Response length (default: 2048)
- `temperature` - Creativity (default: 0.3, lower = more focused)

## RAG Integration

To add RAG (document retrieval):

1. Store medical documents in S3 or local vector DB
2. Retrieve relevant documents based on user query
3. Inject retrieved context into the prompt:

```python
def query_with_rag(user_prompt: str, context: str) -> str:
    full_prompt = f"Context:\n{context}\n\nQuestion: {user_prompt}"
    return query(full_prompt)
```

3. Use services like:
   - **Amazon Kendra** - Document search
   - **Pinecone/Weaviate** - Vector database
   - **LangChain** - RAG framework

## Medical Use Cases

- Cancer symptom information
- Treatment options overview
- Clinical trial finder
- Medication interactions
- Support resources

**Note**: Always include disclaimer that this is informational, not medical advice.

## Troubleshooting

- **Slow responses**: 120B model takes time. Normal behavior.
- **AccessDenied**: IAM role lacks permissions
- **Model not found**: Verify region is `us-east-1`