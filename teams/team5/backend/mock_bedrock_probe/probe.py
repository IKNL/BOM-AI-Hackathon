"""Standalone Mantle/OpenAI-compatible Bedrock probe.

This module intentionally avoids the app's runtime wiring. It reads the
project .env file directly, inspects the temporary Mantle bearer token, and
performs a minimal connectivity test against the OpenAI-compatible endpoint.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_MODEL = "openai.gpt-oss-120b"
TOKEN_PREFIX = "bedrock-api-key-"


@dataclass
class ProbeResult:
    env_path: str
    openai_base_url: str
    model: str
    sts_status: str
    sts_reason: str
    token_metadata: dict[str, Any]
    models_check: dict[str, Any]
    responses_check: dict[str, Any]


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def inspect_mantle_token(api_key: str, now_utc: datetime) -> tuple[str, str, dict[str, Any]]:
    if not api_key:
        return "missing", "OPENAI_API_KEY is empty", {}

    if not api_key.startswith(TOKEN_PREFIX):
        return "unknown", "OPENAI_API_KEY is not a Mantle token", {"prefix": api_key[:24]}

    raw_query = api_key[len(TOKEN_PREFIX) :]
    parsed = {key: values[0] for key, values in parse_qs(raw_query, keep_blank_values=True).items()}

    issued_at_raw = parsed.get("X-Amz-Date")
    expires_raw = parsed.get("X-Amz-Expires")
    access_key_id = parsed.get("X-Amz-Credential", "").split("/")[0]

    metadata: dict[str, Any] = {
        "access_key_id_prefix": access_key_id[:8] if access_key_id else "",
        "has_session_token": "X-Amz-Security-Token" in parsed,
        "signed_headers": parsed.get("X-Amz-SignedHeaders", ""),
        "action": parsed.get("Action", ""),
        "issued_at_utc": None,
        "expires_at_utc": None,
        "expired_by_clock": None,
    }

    if not issued_at_raw or not expires_raw:
        return "unknown", "Mantle token is missing X-Amz-Date or X-Amz-Expires", metadata

    issued_at = datetime.strptime(issued_at_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    expires_at = issued_at + timedelta(seconds=int(expires_raw))
    expired = now_utc >= expires_at

    metadata["issued_at_utc"] = issued_at.isoformat()
    metadata["expires_at_utc"] = expires_at.isoformat()
    metadata["expired_by_clock"] = expired

    if expired:
        return "expired", "Mantle token is past its signed expiry window", metadata

    return "active_window", "Mantle token is still inside its signed expiry window", metadata


def make_request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = client.request(method, path, json=json_body)
        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return {
            "ok": response.is_success,
            "status_code": response.status_code,
            "body": payload,
        }
    except Exception as exc:  # pragma: no cover - runtime guard
        return {
            "ok": False,
            "status_code": None,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def classify_sts_status(
    token_status: str,
    models_check: dict[str, Any],
    responses_check: dict[str, Any],
) -> tuple[str, str]:
    if token_status == "missing":
        return "missing", "No Mantle token was configured"
    if token_status == "expired":
        return "revoked_or_expired", "The Mantle token is already outside its signed lifetime"

    for check in (models_check, responses_check):
        status_code = check.get("status_code")
        body = json.dumps(check.get("body", "")) if "body" in check else check.get("error", "")
        if status_code in {401, 403}:
            return "revoked_or_denied", f"Auth failed with HTTP {status_code}: {body[:300]}"

    if models_check.get("ok") or responses_check.get("ok"):
        return "active", "At least one authenticated Mantle request succeeded"

    if models_check.get("status_code") is None and responses_check.get("status_code") is None:
        return "unreachable", "Both checks failed before an HTTP response was returned"

    return "unknown", "The token is not expired by clock, but the endpoint did not clearly authenticate"


def run_probe(model: str = DEFAULT_MODEL) -> ProbeResult:
    env = load_env_file(ENV_PATH)
    base_url = env.get("OPENAI_BASE_URL", "").rstrip("/")
    api_key = env.get("OPENAI_API_KEY", "")
    now_utc = datetime.now(UTC)

    token_status, token_reason, token_metadata = inspect_mantle_token(api_key, now_utc)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(30.0, connect=10.0)
    with httpx.Client(base_url=base_url, headers=headers, timeout=timeout) as client:
        models_check = make_request(client, "GET", "/models")
        responses_check = make_request(
            client,
            "POST",
            "/responses",
            json_body={
                "model": model,
                "input": [
                    {
                        "role": "user",
                        "content": "Write a one-sentence bedtime story about a unicorn.",
                    }
                ],
            },
        )

    sts_status, sts_reason = classify_sts_status(token_status, models_check, responses_check)

    return ProbeResult(
        env_path=str(ENV_PATH),
        openai_base_url=base_url,
        model=model,
        sts_status=sts_status,
        sts_reason=sts_reason,
        token_metadata=token_metadata | {"token_window_status": token_status, "token_window_reason": token_reason},
        models_check=models_check,
        responses_check=responses_check,
    )


def main() -> int:
    model = os.environ.get("BEDROCK_PROBE_MODEL", DEFAULT_MODEL)
    result = run_probe(model=model)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
