from autoharness.benchmarks.fixtures import FixtureBenchmark


def test_fixture_benchmark_script_advances_observation_and_actions() -> None:
    benchmark = FixtureBenchmark(
        script=[
            {"observation": "Legal Actions: 'north'", "valid_actions": ["north"]},
            {"observation": "Legal Actions: 'east'", "valid_actions": ["east"]},
        ]
    )

    benchmark.reset()

    assert benchmark.get_observation() == "Legal Actions: 'north'"
    assert benchmark.available_actions() == ["north"]
    first_outcome = benchmark.step("north")
    assert first_outcome.done is False
    assert benchmark.get_observation() == "Legal Actions: 'east'"
    assert benchmark.available_actions() == ["east"]
    second_outcome = benchmark.step("east")
    assert second_outcome.done is True
