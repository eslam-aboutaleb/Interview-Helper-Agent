# Infrastructure (Terraform)

This directory contains the Terraform configuration that replaces
the old interactive `AWSdeployment.sh` script. It provisions the
complete AWS stack for the Interview Helper application.

## Architecture

```
Internet
   │
   ├── EC2 (public subnet) ── Docker Compose stack
   │      ├── frontend  (nginx, :80)
   │      └── backend   (FastAPI, :8000)
   │              │
   │              ├── containerized postgres (default), or
   │              └── RDS PostgreSQL (use_rds = true, private subnet)
   │
   └── (optional) Route53 + ACM for a custom domain
```

## Quick start

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars (set db_password, gemini_api_key, allowed_ssh_cidr)

terraform init
terraform plan
terraform apply
```

After apply, the outputs show the frontend URL, API URL, and an
SSM command for keyless shell access:

```bash
aws ssm start-session --target <instance-id> --region eu-north-1
```

## Two database modes

| Mode                   | Config            | What runs                                                              |
| ---------------------- | ----------------- | ---------------------------------------------------------------------- |
| Container DB (default) | `use_rds = false` | postgres:15 container on the EC2 (data in a Docker volume)             |
| Managed RDS            | `use_rds = true`  | RDS PostgreSQL in private subnets; the Compose `db` service is skipped |

## Key variables

| Variable                            | Default                       | Purpose                               |
| ----------------------------------- | ----------------------------- | ------------------------------------- |
| `aws_region`                        | `eu-north-1`                  | Deployment region                     |
| `instance_type`                     | `t3.medium`                   | EC2 size                              |
| `use_rds`                           | `false`                       | Provision RDS instead of container DB |
| `db_password`                       | (sensitive)                   | PostgreSQL password                   |
| `gemini_api_key`                    | (sensitive)                   | Injected into the backend container   |
| `allowed_ssh_cidr`                  | `0.0.0.0/0`                   | Restrict to your IP in production     |
| `key_name`                          | `""`                          | EC2 key pair; leave empty and use SSM |
| `repo_url` / `repo_branch`          | GitHub repo / `master`        | What the instance clones and runs     |
| `llm_model` / `llm_fallback_models` | `gemini/gemini-1.5-flash` / … | LiteLLM provider chain                |

## Secrets

`db_password` and `gemini_api_key` are marked `sensitive`. Prefer
passing them via `TF_VAR_` environment variables or a git-ignored
`terraform.tfvars` over committing them. For production, store them
in AWS Secrets Manager or SSM Parameter Store and reference them
with `data` sources.

## Remote state

`versions.tf` contains a commented-out S3 backend block. Uncomment
it (with a DynamoDB lock table) for team or production use so state
is shared and locked during applies.

## Custom domain (optional)

Set `domain_name` and `hosted_zone_id` to attach the instance's
public DNS to a Route53 record. HTTPS termination requires an ACM
certificate and an ALB/CloudFront in front of the instance — a
follow-up enhancement.

## Destroy

```bash
terraform destroy
```

Note: with `use_rds = true` and `skip_final_snapshot = true`, the
database is destroyed without a final snapshot. Enable snapshots
(`final_snapshot_identifier`) before destroying production data.
