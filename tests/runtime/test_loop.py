# Requirement coverage:
# REQ-001-bootstrap-002, REQ-001-bootstrap-004
# REQ-006-provider-backed-probe-cost-auth-policy-012
from autoharness.benchmarks.fixtures import FixtureBenchmark
from autoharness.providers.base import GenerationConfig, ProviderResult
from autoharness.providers.fixture import FixtureProvider
from autoharness.runtime.loop import run_episode


def test_run_episode_retries_once_then_succeeds(tmp_path) -> None:
    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    provider = FixtureProvider(sequence=["right", "left"])
    result = run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=2,
        artifact_root=tmp_path,
    )
    assert result.status == "passed"
    assert result.retry_count == 1


def test_run_episode_writes_failure_bundle_when_retries_exhausted(tmp_path) -> None:
    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    provider = FixtureProvider(sequence=["right", "right"])
    result = run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=1,
        artifact_root=tmp_path,
    )
    assert result.status == "failed"
    assert (tmp_path / "failure-bundle.json").exists()


def test_run_episode_persists_summary_with_paths(tmp_path) -> None:
    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    provider = FixtureProvider(sequence=["left"])
    result = run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=0,
        artifact_root=tmp_path,
    )
    assert result.status == "passed"
    summary_text = (tmp_path / "run-summary.json").read_text()
    assert '"summary_path": null' not in summary_text
    assert '"trace_path": null' not in summary_text


def test_run_episode_includes_warning_context_after_illegal_action(tmp_path) -> None:
    prompts: list[str] = []

    class RecordingProvider:
        def __init__(self) -> None:
            self._responses = iter(["right", "left"])

        def generate(self, prompt: str) -> ProviderResult:
            prompts.append(prompt)
            return ProviderResult(
                text=next(self._responses),
                provider="recording",
                model="test-model",
            )

    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    result = run_episode(
        benchmark=benchmark,
        provider=RecordingProvider(),
        retry_limit=2,
        artifact_root=tmp_path,
    )
    assert result.status == "passed"
    assert len(prompts) == 2
    assert "Previous action 'right' was illegal." in prompts[1]


def test_run_episode_reports_legal_action_rate_and_reward(tmp_path) -> None:
    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    provider = FixtureProvider(sequence=["right", "left"])

    result = run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=1,
        artifact_root=tmp_path,
    )

    assert result.status == "passed"
    assert result.legal_attempts == 1
    assert result.illegal_attempts == 1
    assert result.legal_action_rate == 0.5
    assert result.total_reward == 1.0


def test_run_episode_reranks_candidates_using_verifiers(tmp_path) -> None:
    captured_configs: list[GenerationConfig | None] = []

    class MultiCandidateProvider:
        def generate(self, prompt: str) -> ProviderResult:
            raise AssertionError(f"unexpected single-candidate call for prompt: {prompt}")

        def generate_candidates(
            self, prompt: str, generation_config: GenerationConfig | None = None
        ) -> list[ProviderResult]:
            del prompt
            captured_configs.append(generation_config)
            return [
                ProviderResult(text="right", provider="multi", model="test-model"),
                ProviderResult(
                    text='{"move":"left"}',
                    provider="multi",
                    model="test-model",
                    metadata={"parsed_response": {"move": "left"}},
                ),
            ]

    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    result = run_episode(
        benchmark=benchmark,
        provider=MultiCandidateProvider(),
        retry_limit=0,
        artifact_root=tmp_path,
        candidate_count=2,
    )
    assert result.status == "passed"
    assert captured_configs
    assert captured_configs[0] is not None
    assert captured_configs[0].candidate_count == 2
    assert captured_configs[0].response_schema == {
        "type": "object",
        "properties": {
            "move": {"type": "string", "enum": ["left"]},
        },
        "required": ["move"],
    }
    trace_text = (tmp_path / "trace.json").read_text()
    assert '"selected_candidate_index": 1' in trace_text
    assert '"legality": 1.0' in trace_text
    assert '"state_consistency": 1.0' in trace_text


def test_run_episode_normalizes_single_embedded_legal_action(tmp_path) -> None:
    benchmark = FixtureBenchmark(valid_actions=["[3, 0]", "[3, 1]", "[3, 2]"], max_steps=1)
    provider = FixtureProvider(sequence=["[Black] [3, 1]"])

    result = run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=0,
        artifact_root=tmp_path,
    )

    assert result.status == "passed"
    trace_text = (tmp_path / "trace.json").read_text()
    assert '"action": "[3, 1]"' in trace_text


def test_run_episode_writes_critic_summary_on_failure(tmp_path) -> None:
    benchmark = FixtureBenchmark(valid_actions=["left"], max_steps=1)
    provider = FixtureProvider(sequence=["right", "right"])
    result = run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=1,
        artifact_root=tmp_path,
    )
    assert result.status == "failed"
    critic_text = (tmp_path / "critic-summary.json").read_text()
    assert '"failure_type": "repeated_invalid"' in critic_text
    assert '"current_legal_actions"' in critic_text
