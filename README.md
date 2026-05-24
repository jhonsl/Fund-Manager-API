# Fund Manager API

Technical challenge — REST API that lets clients manage their
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

## Initialize the data model

A single-table design (`fund_manager`, generic `PK`/`SK` + one `GSI1`) backs all
entities. Create the table and seed the fixed fund catalog with two idempotent
scripts (run from the repo root, venv active, DynamoDB Local up):

```bash
python -m scripts.create_table   # create the table + GSI1 (skips if it exists)
python -m scripts.seed_funds     # insert the 5 funds (skips ones already present)
```

Both are safe to re-run. The endpoint comes from `.env`
(`DYNAMODB_ENDPOINT_URL`), so make sure it points at DynamoDB Local
(`http://localhost:8002`) when running outside Docker.

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

## Authentication & authorization

The API uses JWT bearer authentication with role-based access control.

```bash
# 1. Register (public) — always creates a CLIENT with the initial balance
curl -X POST localhost:8080/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"ana@x.com","password":"secret123","phone":"+57300","notify_pref":"EMAIL"}'

# 2. Login (form-encoded) — returns a JWT access token
curl -X POST localhost:8080/api/v1/auth/login \
  -d 'username=ana@x.com&password=secret123'

# 3. Call protected endpoints with the token
curl localhost:8080/api/v1/funds -H 'Authorization: Bearer <token>'
```

In Swagger UI (`/docs`) use the **Authorize** button to log in and call endpoints.

**Roles & ownership:**

- `CLIENT` — may subscribe/cancel/view history only for **their own** `client_id`.
- `ADMIN` — may access **any** client's data. Admins are created out-of-band:

```bash
python -m scripts.seed_admin --email admin@btg.com --password "<strong-password>"
```

## Security

- **Passwords**: hashed with **bcrypt**; never stored or returned in plaintext.
- **Tokens**: **HS256-signed JWT** (access token, 30 min). `JWT_SECRET_KEY` must be
  set via env var / AWS Secrets Manager in production — the app refuses to start
  in `prod` with the default value.
- **Authorization**: role-based (CLIENT/ADMIN) plus per-resource ownership checks.
- **In transit**: HTTPS/TLS terminated at the AWS load balancer / API Gateway.
- **At rest**: DynamoDB server-side encryption (enabled by default on AWS).
- Unexpected errors return a generic 500 (no stack traces leaked to clients).

## Test

```bash
pytest            # runs tests with coverage (fails under 90%)
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
