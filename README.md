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

## Run

```bash
uvicorn app.main:app --reload
```

Then open:

- API root health check: http://localhost:8000/health
- Interactive docs (Swagger UI): http://localhost:8000/docs

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
