# Terraform Infrastructure

Independent Terraform stacks for Alex, deployed in order:

| Directory | Resources |
|-----------|-----------|
| `2_sagemaker/` | SageMaker serverless embedding endpoint |
| `3_ingestion/` | S3 Vectors, ingest Lambda, API Gateway |
| `4_researcher/` | Researcher agent (App Runner) — optional |
| `5_database/` | Aurora Serverless v2 + Data API |
| `6_agents/` | Agent Lambdas + SQS |
| `7_frontend/` | API Lambda, API Gateway, S3, CloudFront |

## Deploy

```bash
cd terraform/2_sagemaker   # then 3, 4, 5, 6, 7
terraform init
terraform plan
terraform apply
```

Copy each `terraform.tfvars.example` to `terraform.tfvars` and fill in values from prior stack outputs.

## Destroy

Destroy in reverse order (7 → 6 → 5 → … → 2):

```bash
terraform destroy
```

## Environment variables

Root `.env` is populated from Terraform outputs — see `.env.example`. Key cross-stack values:

- `VECTOR_BUCKET`, `ALEX_API_*` — from `3_ingestion`
- `AURORA_*` — from `5_database`
- `SQS_QUEUE_URL` — from `6_agents`

## State

Each directory uses local `terraform.tfstate` (gitignored). Back up state files before major changes.
