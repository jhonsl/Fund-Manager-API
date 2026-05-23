# Fund Manager API

BTG Pactual technical challenge — REST API that lets clients manage their
investment funds (subscribe, cancel, view transaction history, notifications).

Built with **Python + FastAPI** over a **NoSQL (DynamoDB)** data model, following
**Clean Architecture**.

## Requirements

- Python >= 3.12

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell)
# source .venv/bin/activate    # macOS / Linux

# 2. Install dependencies (incl. dev tools)
pip install -e ".[dev]"

# 3. Create your local env file
copy .env.example .env         # Windows
# cp .env.example .env          # macOS / Linux
```

## Run with Docker (recommended)

The whole stack — API, DynamoDB Local, and a web admin UI — runs with one command.
Requires Docker Desktop running.

```bash
docker compose up -d --build   # build + start everything
docker compose ps              # check status
docker compose logs -f api     # follow API logs
docker compose down            # stop (keeps data)
docker compose down -v         # stop and wipe data
```

Ports (host -> container):

| Service        | Host port | URL                   |
| -------------- | --------- | --------------------- |
| API (uvicorn)  | 8080      | http://localhost:8080 |
| DynamoDB Local | 8002      | http://localhost:8002 |
| DynamoDB Admin | 8001      | http://localhost:8001 |

> The API container has hot-reload enabled (the `./app` folder is mounted), so
> code edits reload automatically — no rebuild needed for source changes.

Then open:

- Health check: http://localhost:8080/health
- Interactive docs (Swagger UI): http://localhost:8080/docs
- DynamoDB Admin (browse tables/items): http://localhost:8001

## Inspecting the database

The bundled **DynamoDB Admin** web UI (http://localhost:8001) lists tables and
items with no extra setup.

For a richer, visual tool you can also use AWS's official **NoSQL Workbench**
(desktop app): add a *DynamoDB local* connection pointing to `localhost:8002`.
See https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/workbench.settingup.html

## Run without Docker

Point your `.env` at the DynamoDB Local host port (`DYNAMODB_ENDPOINT_URL=http://localhost:8002`),
then:

```bash
python -m app.main         # uses PORT from settings (default :8080)
# or explicitly:
uvicorn app.main:app --reload --port 8080
```

## Test

```bash
pytest
```

## Project structure

```
app/
├── domain/          # Entities, value objects, repository interfaces, exceptions
├── application/     # Use cases, DTOs, service interfaces
├── infrastructure/  # DynamoDB repos, notifications (SES/SNS), security, config
├── presentation/    # FastAPI routes, schemas, dependencies, middleware
└── main.py          # App entry point
infra/               # AWS CloudFormation (IaC)
tests/               # Unit and integration tests
```
