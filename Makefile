.PHONY: setup dev test lint typecheck verify preflight-dry-run preflight-dev-test verify-practical-path verify-practical-path-runtime
VERIFY_ARTIFACT_ROOT ?= tmp/verify-artifacts
PREFLIGHT_MANIFEST ?= manifests/provider_probe_model_preflight_free.yaml
PREFLIGHT_ARTIFACT_ROOT ?= tmp/provider-probes/model-preflight-dev
PREFLIGHT_MAX_SPEND_USD ?= 1.00

setup:
	uv sync --extra dev --extra textarena

dev:
	uv run --extra dev --extra textarena python -m autoharness --help

lint:
	uv run --extra dev --extra textarena ruff check .

test:
	uv run --extra dev --extra textarena pytest

typecheck:
	uv run --extra dev --extra textarena mypy src

verify: lint test typecheck
	uv run --extra dev --extra textarena python -m autoharness verify --manifest manifests/offline_smoke.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/offline-smoke
	uv run --extra dev --extra textarena python -m autoharness verify --manifest manifests/toy_dev.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/toy-dev
	uv run --extra dev --extra textarena python -m autoharness verify --manifest manifests/toy_holdout.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/toy-holdout
	uv run --extra dev --extra textarena python -m autoharness verify --manifest manifests/textarena_tictactoe_smoke.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/textarena-tictactoe-smoke
	uv run --extra dev --extra textarena python -m autoharness verify --manifest manifests/textarena_othello_smoke.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/textarena-othello-smoke
	uv run --extra dev --extra textarena python -m autoharness verify --manifest manifests/textarena_pigdice_smoke.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/textarena-pigdice-smoke
	uv run --extra dev --extra textarena python -m autoharness campaign --candidate tests/fixtures/candidates/ttt_first_historical_move.py --dev-manifest manifests/toy_refinement_dev.yaml --holdout-manifest manifests/toy_refinement_holdout.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/toy-refinement-campaign --patch-text "Parse the final Available Moves block and emit exactly one move." --max-iterations 1
	uv run --extra dev --extra textarena python -m autoharness benchmark --matrix manifests/toy_benchmark_matrix.yaml --artifact-root $(VERIFY_ARTIFACT_ROOT)/toy-benchmark-matrix

preflight-dry-run:
	uv run --extra dev --extra textarena --extra preflight python -m autoharness provider-probe --manifest $(PREFLIGHT_MANIFEST) --artifact-root $(PREFLIGHT_ARTIFACT_ROOT) --max-spend-usd $(PREFLIGHT_MAX_SPEND_USD)

preflight-dev-test:
	uv run --extra dev --extra textarena --extra preflight python -m autoharness provider-probe --manifest $(PREFLIGHT_MANIFEST) --artifact-root $(PREFLIGHT_ARTIFACT_ROOT) --max-spend-usd $(PREFLIGHT_MAX_SPEND_USD) --usage-policy allow-missing-once --run

verify-practical-path:
	uv run python scripts/verify_practical_path.py
	uv run pytest tests/practical tests/search tests/artifacts tests/refinement tests/providers tests/benchmarking tests/sandbox -q

verify-practical-path-runtime:
	tmp_dir="$$(mktemp -d)"; \
	uv run python scripts/verify_practical_path.py --artifact-root "$$tmp_dir/practical-path" --status-report "$$tmp_dir/status.md"; \
	rm -rf "$$tmp_dir"
