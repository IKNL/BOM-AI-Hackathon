"""LLM-as-judge for scoring chunk relevance to a query."""

import json
import logging
import os

import litellm

logger = logging.getLogger(__name__)

MODEL = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")


async def judge_relevance(query: str, chunk: str) -> float:
    """Score how relevant a chunk is to a query. Returns 0.0 or 1.0."""
    prompt = f"""You are a relevance judge. Score whether the following text chunk is relevant to the user's query.

Query: "{query}"

Text chunk:
\"\"\"
{chunk[:1500]}
\"\"\"

Is this chunk relevant to answering the query? Reply with ONLY a JSON object:
{{"relevant": true}} or {{"relevant": false}}"""

    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        result = json.loads(clean.strip())
        return 1.0 if result.get("relevant", False) else 0.0
    except Exception as e:
        logger.warning("Judge call failed: %s", e)
        return 0.0


async def judge_batch(query: str, chunks: list[str]) -> list[float]:
    """Score a batch of chunks for relevance to a query."""
    import asyncio
    tasks = [judge_relevance(query, chunk) for chunk in chunks]
    return await asyncio.gather(*tasks)
