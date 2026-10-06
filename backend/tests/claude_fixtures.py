"""Client Claude simulé : les requêtes envoyées sont conservées pour être vérifiées."""

import anthropic
import httpx2

REQUESTS: list[dict] = []


def message(text: str = "## But du jeu\nGagner.", stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}] if text else [],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


def claude_client(body: dict | None = None, status: int = 200) -> anthropic.Anthropic:
    import json

    def handler(request: httpx2.Request) -> httpx2.Response:
        REQUESTS.append({"headers": dict(request.headers), "json": json.loads(request.content)})
        if status != 200:
            return httpx2.Response(
                status, json={"type": "error", "error": {"type": "api_error", "message": "x"}}
            )
        return httpx2.Response(200, json=body or message())

    return anthropic.Anthropic(
        api_key="cle-claude",
        max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
