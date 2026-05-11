# Model Providers

AutoHarness keeps model-provider setup in manifests. The public package supports deterministic fixtures for CI, [ModelPreflight](https://github.com/pylit-ai/model-preflight) routes for small provider checks, direct Gemini paths, OpenRouter, and local candidate modules.

Use fixtures first. Move to hosted models only when the benchmark, artifact root, expected budget, and credential source are explicit.

## Install Extras

Core development:

```bash
uv sync --extra dev
```

Provider adapters:

```bash
uv sync --extra dev --extra providers
```

[ModelPreflight](https://github.com/pylit-ai/model-preflight)-backed provider checks:

```bash
uv sync --extra dev --extra preflight
```

TextArena plus all provider surfaces:

```bash
uv sync --extra dev --extra textarena --extra providers --extra preflight
```

## Provider Choices

| Provider kind | Use when | Credential path | Notes |
| --- | --- | --- | --- |
| `fixture` | CI, manifest development, verifier debugging | none | Deterministic and safest default. |
| `candidate` | Running local candidate code as the actor | local Python module or Docker image | Good for comparing generated agents without a hosted model call. |
| `model-preflight` | Smoke tests and small exploratory route checks | ModelPreflight local config | Stable groups such as `free_reasoning`; useful before committing to direct provider setup. |
| `gemini-cli` | You already use the Gemini CLI locally | CLI OAuth session | Supported by `provider-probe` preflight. |
| `gemini` | Direct Gemini SDK or Vertex AI runs | ADC or API key | `provider-probe` expects Vertex/ADC; API-key mode is available for normal provider execution. |
| `openrouter` | You want an OpenAI-compatible hosted route through OpenRouter | `OPENROUTER_API_KEY` or custom env var | Adapter exists for normal provider execution; `provider-probe` preflight does not yet guard this route. |

## Manifest Shape

Every provider lives under the manifest `provider` key:

```yaml
provider:
  kind: fixture
  model: fixture-model
  candidate_count: 1
  temperature: 0
```

Common fields:

- `kind`: provider adapter name.
- `model`: provider model id, ModelPreflight group, or local model label.
- `auth.kind`: one of `none`, `api-key`, `oauth-adc`, or `oauth-cli`.
- `auth.env_var`: environment variable for API-key providers.
- `auth.project` and `auth.location`: Google Cloud project and location for Vertex/ADC.
- `candidate_count`: number of generations requested for each prompt.
- `temperature` and `top_p`: optional generation controls.
- `options`: provider-specific settings such as CLI command or timeout.

## ModelPreflight

Use [ModelPreflight](https://github.com/pylit-ai/model-preflight) when you want route checks before wiring a direct provider account into AutoHarness.

Example:

```yaml
provider:
  kind: model-preflight
  model: free_reasoning
  candidate_count: 1
```

Dry-run the probe. Omit `--run` to avoid generation:

```bash
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_model_preflight_free.yaml \
  --artifact-root tmp/provider-probes/model-preflight-free \
  --max-spend-usd 1.00
# Provider probe dry-run passed (.../provider-probe-preflight.json, .../provider-probe-budget.json)
```

Run only after the dry-run evidence is acceptable:

```bash
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_model_preflight_free.yaml \
  --artifact-root tmp/provider-probes/model-preflight-free-live \
  --max-spend-usd 1.00 \
  --run
# Provider probe passed for run <run-id>
```

## Gemini CLI

Use `gemini-cli` when the `gemini` command is installed, on `PATH`, and authenticated.

Example:

```yaml
provider:
  kind: gemini-cli
  model: gemini-2.5-flash
  auth:
    kind: oauth-cli
  candidate_count: 1
  temperature: 0
  options:
    command: gemini
    timeout_seconds: 120
```

Canary dry-run:

```bash
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_gemini_othello.yaml \
  --artifact-root tmp/provider-probes/gemini-othello \
  --max-spend-usd 1.00
# Provider probe dry-run passed (.../provider-probe-preflight.json, .../provider-probe-budget.json)
```

Live canary:

```bash
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_gemini_othello.yaml \
  --artifact-root tmp/provider-probes/gemini-othello-live \
  --max-spend-usd 1.00 \
  --run
# Provider probe passed for run <run-id>
```

## Gemini SDK

Use `gemini` when you want direct SDK access. For guarded `provider-probe` runs, use Vertex/ADC style auth:

```yaml
provider:
  kind: gemini
  model: gemini-2.5-flash
  auth:
    kind: oauth-adc
    project: your-google-cloud-project
    location: us-central1
  candidate_count: 1
  temperature: 0
```

You can provide the project through `GOOGLE_CLOUD_PROJECT` or `GCLOUD_PROJECT` instead of putting it in the manifest.

API-key mode is available for normal provider execution:

```yaml
provider:
  kind: gemini
  model: gemini-2.5-flash
  auth:
    kind: api-key
    env_var: GEMINI_API_KEY
  candidate_count: 1
```

The guarded `provider-probe` preflight does not silently switch to API-key mode. For API-key canaries, use a small `verify` manifest with an isolated artifact root:

```bash
uv run autoharness verify \
  --manifest manifests/your-gemini-api-key-canary.yaml \
  --artifact-root tmp/provider-runs/gemini-api-key-canary
# Verification passed for run <run-id>
```

## OpenRouter

Use OpenRouter when you want a provider route behind an OpenAI-compatible chat-completions API.

```yaml
provider:
  kind: openrouter
  model: provider/model-name
  auth:
    kind: api-key
    env_var: OPENROUTER_API_KEY
  candidate_count: 1
  temperature: 0
```

Run a small canary with `verify`:

```bash
uv run autoharness verify \
  --manifest manifests/your-openrouter-canary.yaml \
  --artifact-root tmp/provider-runs/openrouter-canary
# Verification passed for run <run-id>
```

OpenRouter is not currently covered by `provider-probe` preflight. Use provider-side quotas, a low `candidate_count`, a tiny benchmark, and an isolated artifact root until a guarded preflight is added.

## Local Candidate Modules

Use `candidate` when a local Python module or Docker image should play the benchmark role:

```yaml
provider:
  kind: candidate
  model: local-candidate
  path: candidates/my_agent.py
  candidate_count: 1
```

For Docker-backed candidates:

```yaml
provider:
  kind: candidate
  model: docker-candidate
  path: candidates/my_agent.py
  use_docker: true
  sandbox_image: python:3.12-alpine
```

## Scaling Up

Do not jump from a dry-run to a large hosted run. Scale in stages:

1. Run fixture or local-candidate manifests in CI.
2. Run `provider-probe` without `--run` for ModelPreflight, Gemini CLI, or Gemini ADC.
3. Run one live canary with `--max-spend-usd`, `candidate_count: 1`, and a new artifact root.
4. Run a small seed sweep with separate artifact roots per provider/model/seed.
5. Summarize probe roots:

```bash
uv run autoharness provider-report \
  --probe-root tmp/provider-probes \
  --output-root tmp/provider-reports/latest
# Provider evidence report written to .../provider-evidence-report.json and .../provider-evidence-report.md
```

6. Increase volume only after the report shows legal-action rate, retries, latency, usage metadata, and spend are acceptable.

Current runner behavior is local and sequential. For larger batches, launch independent manifests with separate artifact roots and external job control, then aggregate the resulting probe or benchmark reports. Keep provider quotas and budget controls in the provider account as well as in AutoHarness command flags.

## Safety Checklist

- Keep API keys in environment variables, not manifests.
- Use a fresh artifact root for each live run.
- Set `candidate_count: 1` until the canary is stable.
- Prefer `provider-probe` where supported because it writes preflight and budget evidence before a live call.
- Use `provider-report` before comparing provider-backed results.
- Treat missing usage metadata as a reason to keep the run exploratory, not production evidence.
