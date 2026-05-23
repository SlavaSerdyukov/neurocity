from __future__ import annotations

import httpx


async def ollama_complete(prompt: str, model: str, base_url: str, timeout: float = 6.0) -> str | None:
    """Best-effort local Ollama completion for narrative flavor only."""

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.35}},
            )
            response.raise_for_status()
            payload = response.json()
            text = str(payload.get("response", "")).strip()
            return text or None
    except (httpx.HTTPError, ValueError):
        return None

