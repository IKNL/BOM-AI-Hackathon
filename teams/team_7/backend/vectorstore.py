"""Load the ChromaDB vector store for retrieval."""

import os

import boto3
import chromadb
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma

from config import settings

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")


def get_vectorstore() -> Chroma:
    bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        aws_session_token=settings.aws_session_token or None,
    )
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v2:0",
    )
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return Chroma(
        client=client,
        collection_name="kanker_nl",
        embedding_function=embeddings,
    )


def retrieve(query: str, k: int = 5) -> list[dict]:
    """Return top-k relevant chunks with metadata."""
    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=k)
    return [
        {"text": doc.page_content, "url": doc.metadata.get("url", "")}
        for doc in docs
    ]
