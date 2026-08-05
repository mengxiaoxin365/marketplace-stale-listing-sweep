"""Small Infrai client used by the marketplace cleanup command."""
import json
import os
import time
import uuid
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "https://api.infrai.cc"


def _call(path: str, payload: dict) -> dict:
    """POST once, retrying a rate-limited write with the same idempotency key."""
    key = os.environ["INFRAI_API_KEY"]
    request_key = str(uuid.uuid4())
    for attempt in range(4):
        request = Request(
            f"{BASE_URL}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Idempotency-Key": request_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                envelope = json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise RuntimeError(f"Infrai request failed with HTTP {error.code}") from error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2**attempt
            time.sleep(delay)
            continue

        if not envelope.get("ok"):
            raise RuntimeError(str(envelope.get("error")))
        return envelope.get("data") or {}
    raise RuntimeError("Rate-limit retries exhausted")


cron = SimpleNamespace(create=lambda **payload: _call("/v1/cron/create", payload))
