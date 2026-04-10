"""Build a local ChromaDB vector store from kanker_nl_pages_all.json."""

import json
import os

import boto3
import chromadb
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "kanker_nl_pages_all.json")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")


def build_vectorstore():
    # Load the JSON data
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        pages = json.load(f)

    print(f"Loaded {len(pages)} pages (using first 200)")

    # Create text splitter (chunk into ~4000 char pieces with overlap)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=500,
    )

    # Prepare documents (limit to first 200 pages)
    texts = []
    metadatas = []
    for i, (url, page) in enumerate(pages.items()):
        if i >= 200:
            break
        content = page.get("text", "").strip()
        if not content:
            continue
        chunks = splitter.split_text(content)
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({
                "url": url,
                "kankersoort": page.get("kankersoort", ""),
            })

    print(f"Split into {len(texts)} chunks")

    # Set up Bedrock embeddings
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

    # Build and persist ChromaDB
    print(f"Building vector store at {CHROMA_DIR}...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Process in batches (Chroma has limits on batch size)
    batch_size = 100
    vectorstore = None
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        if vectorstore is None:
            vectorstore = Chroma.from_texts(
                texts=batch_texts,
                metadatas=batch_meta,
                embedding=embeddings,
                client=client,
                collection_name="kanker_nl",
            )
        else:
            vectorstore.add_texts(texts=batch_texts, metadatas=batch_meta)
        print(f"  Indexed {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    print("Done! Vector store built successfully.")


if __name__ == "__main__":
    build_vectorstore()
