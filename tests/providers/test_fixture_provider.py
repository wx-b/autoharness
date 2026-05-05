from autoharness.providers.fixture import FixtureProvider


def test_fixture_provider_returns_deterministic_text() -> None:
    provider = FixtureProvider(response_text="MOVE: center")
    result = provider.generate("pick a move")
    assert result.text == "MOVE: center"
    assert result.provider == "fixture"
