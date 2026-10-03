# ---- AWS / environment ----
variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-north-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project identifier used for resource naming"
  type        = string
  default     = "interview-helper"
}

# ---- Networking ----
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b"]
}

# ---- Compute ----
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH into the EC2 instance. Empty string disables SSH ingress entirely (administer via SSM instead)."
  type        = string
  default     = ""

  validation {
    condition     = var.allowed_ssh_cidr == "" || can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}/[0-9]{1,2}$", var.allowed_ssh_cidr))
    error_message = "allowed_ssh_cidr must be a valid IPv4 CIDR (e.g. 203.0.113.0/24) or an empty string to disable SSH access."
  }
}

# ---- Database ----
variable "use_rds" {
  description = "Provision a managed RDS PostgreSQL instance instead of a containerized DB"
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "RDS instance class (when use_rds = true)"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "interview_prep"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "PostgreSQL master password. Override via TF_VAR_db_password or a tfvars file; never commit real secrets."
  type        = string
  sensitive   = true
  default     = "change-me-in-production"
}

# ---- Application ----
variable "gemini_api_key" {
  description = "Google Gemini API key (injected into the backend container)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "cors_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "*"
}

variable "log_level" {
  description = "Backend log level"
  type        = string
  default     = "INFO"
}

# ---- Domain / TLS ----
variable "domain_name" {
  description = "Optional domain for the frontend (enables HTTPS listener when set)"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for the domain (required if domain_name is set)"
  type        = string
  default     = ""
}

# ---- Application source ----
variable "repo_url" {
  description = "Git repository URL cloned on the EC2 instance"
  type        = string
  default     = "https://github.com/eslam-aboutaleb/Interview-Helper-Agent.git"
}

variable "repo_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "master"
}

# ---- LLM provider (LiteLLM) ----
variable "llm_model" {
  description = "Primary LLM model for LiteLLM (e.g. gemini/gemini-1.5-flash)"
  type        = string
  default     = "gemini/gemini-1.5-flash"
}

variable "llm_fallback_models" {
  description = "Comma-separated fallback models tried when the primary fails"
  type        = string
  default     = "openai/gpt-4o-mini,anthropic/claude-3-5-haiku-20241022"
}
