import asyncio
import json
import re
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from config import settings
from vectorstore import retrieve


def _build_system_prompt(context: list[dict], simplified: bool = False, tone: str | None = None, profile: dict | None = None) -> str:
    context_text = "\n\n---\n\n".join(
        f"Source: {c['url']}\n{c['text']}" for c in context
    )
    system_prompt = (
        "You are a helpful assistant that answers questions about cancer, "
        "based on information from kanker.nl and other reliable Dutch cancer sources. "
        "Use the following context to answer the question. If the answer is not in "
        "the context, say so honestly. Give only a direct answer without reasoning, "
        "explanation of your thought process, or steps. "
        "When you use difficult or medical terms, briefly explain them in simple words. "
        "Always respond in English."
    )
    if simplified:
        system_prompt += (
            " Explain the answer in simple language so that someone without "
            "medical knowledge can understand it. Avoid jargon."
        )
    if tone == "direct":
        system_prompt += " Respond briefly and concisely, just the facts."
    elif tone == "begrijpend":
        system_prompt += " Respond with clear explanations and room for questions."
    elif tone == "empathisch":
        system_prompt += " Respond warmly and compassionately, with attention to feelings."
    if profile:
        profile_parts = []
        if profile.get("kankersoort"):
            profile_parts.append(f"Cancer type: {profile['kankersoort']}")
        if profile.get("stadium"):
            profile_parts.append(f"Stage: {profile['stadium']}")
        if profile.get("behandelingen"):
            profile_parts.append(f"Treatments: {', '.join(profile['behandelingen'])}")
        if profile.get("symptomen"):
            profile_parts.append(f"Symptoms: {', '.join(profile['symptomen'])}")
        if profile_parts:
            system_prompt += "\n\nPatient profile:\n" + "\n".join(profile_parts)
    system_prompt += f"\n\nContext:\n{context_text}"
    return system_prompt


def _get_credentials():
    session = boto3.Session(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        aws_session_token=settings.aws_session_token or None,
        region_name=settings.aws_region,
    )
    return session.get_credentials().get_frozen_credentials()


def _call_bedrock_openai(message: str, context: list[dict], simplified: bool = False, tone: str | None = None, profile: dict | None = None) -> dict:
    credentials = _get_credentials()
    system_prompt = _build_system_prompt(context, simplified, tone, profile)

    url = f"https://bedrock-runtime.{settings.aws_region}.amazonaws.com/openai/v1/chat/completions"
    body = json.dumps({
        "model": settings.bedrock_model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    })

    request = AWSRequest(
        method="POST", url=url, data=body,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(credentials, "bedrock", settings.aws_region).add_auth(request)

    req = urllib.request.Request(
        url=request.url,
        data=body.encode(),
        headers=dict(request.headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Bedrock API error {e.code}: {error_body}") from e

    answer = result["choices"][0]["message"]["content"]
    answer = re.sub(r"<reasoning>.*?</reasoning>\s*", "", answer, flags=re.DOTALL).strip()
    sources = list({c["url"] for c in context if c["url"]})
    return {"answer": answer, "sources": sources}


def _call_bedrock_openai_stream(message: str, context: list[dict], simplified: bool = False, tone: str | None = None, profile: dict | None = None):
    credentials = _get_credentials()
    system_prompt = _build_system_prompt(context, simplified, tone, profile)

    url = f"https://bedrock-runtime.{settings.aws_region}.amazonaws.com/openai/v1/chat/completions"
    body = json.dumps({
        "model": settings.bedrock_model_id,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    })

    request = AWSRequest(
        method="POST", url=url, data=body,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(credentials, "bedrock", settings.aws_region).add_auth(request)

    req = urllib.request.Request(
        url=request.url,
        data=body.encode(),
        headers=dict(request.headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            buffer = ""
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        buffer += content
                        cleaned = re.sub(r"<reasoning>.*?</reasoning>\s*", "", buffer, flags=re.DOTALL)
                        if "<reasoning>" not in buffer:
                            yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Bedrock API error {e.code}: {error_body}") from e


async def chat_with_llm(message: str, simplified: bool = False, tone: str | None = None, profile: dict | None = None) -> dict:
    context = retrieve(message)
    return await asyncio.to_thread(_call_bedrock_openai, message, context, simplified, tone, profile)


async def chat_with_llm_stream(message: str, simplified: bool = False, tone: str | None = None, profile: dict | None = None):
    context = retrieve(message)
    for chunk in _call_bedrock_openai_stream(message, context, simplified, tone, profile):
        yield json.dumps({"content": chunk})
        await asyncio.sleep(0)
