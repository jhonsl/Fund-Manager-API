# Deployment (AWS CloudFormation)

Infrastructure-as-Code for the Fund Manager API. A single CloudFormation
template ([`template.yaml`](template.yaml)) provisions the **entire serverless
backend** on AWS:

| Resource | Purpose |
| --- | --- |
| `AWS::DynamoDB::Table` | Single-table store (`PK`/`SK` + `GSI1`), TTL, SSE-at-rest, point-in-time recovery |
| `AWS::Lambda::Function` (Image) | FastAPI app running via **Mangum**, packaged as a container image from ECR |
| `AWS::ApiGatewayV2::*` | HTTP API Gateway proxying every route to the Lambda |
| `AWS::SecretsManager::Secret` | Auto-generated HS256 JWT signing key, injected as an env var |
| `AWS::IAM::Role` | Least-privilege execution role (DynamoDB + SES/SNS + logs) |
| `AWS::Logs::LogGroup` | CloudWatch log groups with 14-day retention |

```
Internet ──▶ HTTP API Gateway ──▶ Lambda (FastAPI + Mangum) ──▶ DynamoDB
                                          │
                                          ├─▶ Secrets Manager (JWT key, at deploy)
                                          └─▶ SES / SNS (notifications)
```

## Why this shape

- **Serverless**: scales to zero, near-zero cost at rest — ideal for a test/demo.
- **Container-image Lambda**: reuses the same `Dockerfile` (a dedicated `lambda`
  stage), so the artifact that runs in AWS is built from the same source as local.
- **The app stays cloud-agnostic**: the JWT secret is resolved at deploy time and
  passed as the `JWT_SECRET_KEY` env var, so the application code never calls
  Secrets Manager directly — it just reads env vars (pydantic-settings), exactly
  as it does locally.

## Prerequisites

- AWS CLI v2, authenticated with credentials that can create the resources above.
- Docker (to build the Lambda image).
- An ECR repository to hold the image.

Set some shell variables (PowerShell shown; adapt for bash):

```powershell
$AWS_REGION   = "us-east-1"
$ACCOUNT_ID   = (aws sts get-caller-identity --query Account --output text)
$ECR_REPO     = "fund-manager-api"
$IMAGE_TAG    = "latest"
$IMAGE_URI    = "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:$IMAGE_TAG"
$STACK_NAME   = "fund-manager-api"
```

## 1. Build & push the Lambda image to ECR

```powershell
# Create the ECR repo (idempotent — ignore the error if it already exists).
aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION

# Authenticate Docker to ECR.
aws ecr get-login-password --region $AWS_REGION | `
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build the `lambda` stage and push.
docker build --target lambda -t $IMAGE_URI .
docker push $IMAGE_URI
```

> The `lambda` stage uses the official `public.ecr.aws/lambda/python:3.12` base
> image and sets the handler to `app.main.lambda_handler`.

## 2. Deploy the stack

```powershell
aws cloudformation deploy `
  --stack-name $STACK_NAME `
  --template-file infra/template.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --region $AWS_REGION `
  --parameter-overrides Environment=prod ImageUri=$IMAGE_URI
```

`CAPABILITY_NAMED_IAM` is required because the template creates a named IAM role.

Read the outputs (API URL, table name, secret ARN):

```powershell
aws cloudformation describe-stacks --stack-name $STACK_NAME `
  --query "Stacks[0].Outputs" --output table
```

## 3. Seed the fund catalog (and an admin)

The table is created empty by CloudFormation. Seed it by running the existing
scripts **against real AWS** — i.e. with no local DynamoDB endpoint and real
credentials in your shell:

```powershell
$env:DYNAMODB_ENDPOINT_URL = ""          # talk to real AWS, not DynamoDB Local
$env:AWS_REGION            = $AWS_REGION
$env:DYNAMODB_TABLE_NAME   = "fund_manager"

python -m scripts.seed_funds
python -m scripts.seed_admin --email admin@btg.com --password "<strong-password>"
```

Both scripts are idempotent and safe to re-run.

> The table is created by the stack, so **do not** run `scripts.create_table`
> against AWS — IaC owns the schema there. That script remains for local DynamoDB.

## 4. Verify

```powershell
$API = (aws cloudformation describe-stacks --stack-name $STACK_NAME `
  --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text)

Invoke-RestMethod "$API/health"          # {"status":"ok","environment":"prod"}
Start-Process "$API/docs"                # Swagger UI

# Register -> login -> call a protected endpoint
Invoke-RestMethod -Method Post "$API/api/v1/auth/register" `
  -ContentType application/json `
  -Body '{"email":"ana@x.com","password":"secret123","phone":"+57300","notify_pref":"EMAIL"}'
$tok = (Invoke-RestMethod -Method Post "$API/api/v1/auth/login" `
  -Body @{username="ana@x.com";password="secret123"}).access_token
Invoke-RestMethod "$API/api/v1/funds" -Headers @{ Authorization = "Bearer $tok" }
```

## Updating the app

Rebuild + push the image (step 1) with a new tag, then redeploy with the new
`ImageUri`. Using an immutable tag (e.g. the git SHA) instead of `latest` makes
Lambda pick up the new code reliably:

```powershell
$IMAGE_TAG = (git rev-parse --short HEAD)
$IMAGE_URI = "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:$IMAGE_TAG"
docker build --target lambda -t $IMAGE_URI .
docker push $IMAGE_URI
aws cloudformation deploy --stack-name $STACK_NAME --template-file infra/template.yaml `
  --capabilities CAPABILITY_NAMED_IAM --region $AWS_REGION `
  --parameter-overrides Environment=prod ImageUri=$IMAGE_URI
```

## Tear down

```powershell
aws cloudformation delete-stack --stack-name $STACK_NAME --region $AWS_REGION
```

> The DynamoDB table and the JWT secret are deleted with the stack. In a real
> production setup you would add a `DeletionPolicy: Retain` to the table (and a
> recovery window to the secret) to guard against accidental data loss.

## Security notes (maps to challenge point 5)

- **Encryption at rest**: DynamoDB `SSESpecification` enabled; the JWT key lives
  in Secrets Manager (encrypted), never in the template or source.
- **Encryption in transit**: API Gateway serves HTTPS/TLS by default.
- **Least privilege**: the Lambda role grants only the specific DynamoDB actions
  the app uses, plus `ses:SendEmail` / `sns:Publish` for notifications.
- **Secret hygiene**: `JWT_SECRET_KEY` is generated by CloudFormation (64 random
  chars) and resolved at deploy time — it is never committed. The app refuses to
  start in `prod` with the default placeholder secret.
