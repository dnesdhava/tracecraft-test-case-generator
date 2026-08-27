# TraceCraft Test Case Generator

TraceCraft is a local Python application that turns authorized BRD, JIRA, and E2E flow evidence into structured, traceable test-case recommendations. The initial web workspace accepts the project sample formats requested for this repository: Excel BRD, Markdown JIRA story content, and flow-diagram PDF.

## Quick Start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=src python -m tcg.interfaces.web.app
```

Open <http://127.0.0.1:5000>. Select **Load sample set** to run the fictional Demo Bank corpus through intake and normalization. For a fully offline generation demo, set `TCG_AI_PROVIDER=deterministic` before starting the server; the configured production provider is Google AI Studio and requires the backend key.

The same flow is available from the CLI:

```bash
PYTHONPATH=src tcg demo
PYTHONPATH=src tcg run create --project "Payment Review"
```

## Architecture

- `tcg.domain` contains immutable models, ports, and deterministic domain services.
- `tcg.application` coordinates the source-to-output workflow.
- `tcg.infrastructure` contains Excel, Markdown, PDF, file-storage, security, AI, audit, and export adapters.
- `tcg.interfaces.web` provides the enterprise-style browser workspace.
- `tcg.interfaces.cli` provides local command-line operations.

The configured AI provider is Google AI Studio with display label `Gemma 4:31B` and API model ID `gemma-4-31b-it`. Set `TCG_AI_API_KEY` only in the backend environment, and keep `TCG_AI_PROVIDER=google`, `TCG_AI_MODEL_NAME=Gemma 4:31B`, `TCG_AI_MODEL_ID=gemma-4-31b-it`, and `TCG_AI_ENDPOINT=https://generativelanguage.googleapis.com/v1beta`. The browser never receives the key. The adapter reads it at request time, sends it in the `x-goog-api-key` request header, and never writes it to source files, logs, prompts, audit records, or API responses. The deterministic local provider remains available in code for offline tests by selecting `TCG_AI_PROVIDER=deterministic`.

When generation reports that Google AI Studio credentials are unavailable, the backend process was started without a key. Set one of the following in the same terminal that starts the backend, then restart the server:

```bash
export TCG_AI_API_KEY='your-key-value'
# Or use Google's standard variable name:
export GOOGLE_API_KEY='your-key-value'
```

Do not send the key through the browser, paste it into a frontend field, commit it, or send it in chat. For a no-network validation run, use `export TCG_AI_PROVIDER=deterministic` instead.

## Sample Corpus

See [samples/README.md](samples/README.md) for the relationship between the Excel BRD, `PAY-101` JIRA story, and vector flow PDF. The samples use fictional symbolic data only.

## Validation

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
```

The generated cases remain recommendations until an authorized human reviewer approves them. Unsupported formats, ambiguous evidence, unresolved links, and review questions must remain visible rather than being converted into invented business behavior.

## CI/CD

GitHub Actions runs the locked lint, type-check, test, dependency-audit, secret-scan, and package-build checks for pushes and pull requests targeting `main`. Dependencies are resolved from `uv.lock` with `uv sync --locked --extra dev`.

Successful pushes to `main` publish the Python wheel and source distribution as both a retained GitHub Actions artifact and a GitHub Release tagged with the workflow run number. The release deployment uses the exact package artifact produced by CI and GitHub's automatically provided `GITHUB_TOKEN`; no additional repository secret or variable is required. The workflow grants read-only contents access to CI and contents-write access only to the guarded release job.

## Google Cloud Run Deployment

The repository includes a [Dockerfile](Dockerfile) for Cloud Run. It runs the Flask application with Gunicorn, uses the locked runtime dependencies, and listens on Cloud Run's `PORT`. Deploy from the configured Google Cloud project with:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
gcloud run deploy tracecraft-test-case-generator --source . --region YOUR_REGION --allow-unauthenticated
```

Store the Google AI Studio key in Secret Manager and attach it to the service as `TCG_AI_API_KEY`; never put the value in `Dockerfile`, Git, or browser configuration. The application uses `Gemma 4:31B` through model ID `gemma-4-31b-it`. The local filesystem used for runs and audit records is ephemeral on Cloud Run, so durable production records require an external storage service or a suitable persistent design.

## License

This project is available under the [MIT License](LICENSE).
