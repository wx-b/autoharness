# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-002
# REQ-006-provider-backed-probe-cost-auth-policy-006
# REQ-006-provider-backed-probe-cost-auth-policy-009
from types import SimpleNamespace

from autoharness.providers.base import GenerationConfig
from autoharness.providers.gemini import GeminiProvider


def test_gemini_provider_emits_structured_candidates() -> None:
    calls: list[dict[str, object]] = []

    class FakeModels:
        def generate_content(
            self, *, model: str, contents: str, config: dict[str, object] | None = None
        ) -> SimpleNamespace:
            calls.append({"model": model, "contents": contents, "config": config})
            return SimpleNamespace(
                text='{"move":"left"}',
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[SimpleNamespace(text='{"move":"left"}')]
                        )
                    ),
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[SimpleNamespace(text='{"move":"right"}')]
                        )
                    ),
                ],
                usage_metadata=SimpleNamespace(
                    prompt_token_count=11,
                    candidates_token_count=7,
                    total_token_count=18,
                ),
                response_id="resp-123",
            )

    class FakeClient:
        def __init__(self) -> None:
            self.models = FakeModels()

    provider = GeminiProvider(
        model="gemini-2.5-flash",
        auth_kind="oauth-adc",
        client_factory=FakeClient,
    )
    schema = {
        "type": "object",
        "properties": {
            "move": {"type": "string", "enum": ["left", "right"]},
        },
        "required": ["move"],
    }

    results = provider.generate_candidates(
        "Pick a move.",
        GenerationConfig(
            candidate_count=2,
            temperature=0.2,
            top_p=0.9,
            response_schema=schema,
        ),
    )

    assert len(results) == 2
    assert calls == [
        {
            "model": "gemini-2.5-flash",
            "contents": "Pick a move.",
            "config": {
                "candidate_count": 2,
                "temperature": 0.2,
                "top_p": 0.9,
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        }
    ]
    assert results[0].metadata["parsed_response"] == {"move": "left"}
    assert results[0].metadata["usage"] == {
        "prompt_token_count": 11,
        "candidates_token_count": 7,
        "total_token_count": 18,
    }
    assert results[1].metadata["response_id"] == "resp-123"


def test_gemini_provider_preserves_oauth_adc_auth_mode_until_client_build() -> None:
    provider = GeminiProvider(
        model="gemini-2.5-flash",
        auth_kind="oauth-adc",
        project="demo-project",
        location="us-central1",
        client_factory=lambda: object(),
    )

    assert provider.auth_kind == "oauth-adc"
    assert provider.project == "demo-project"
    assert provider.location == "us-central1"
