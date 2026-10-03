terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state is strongly recommended for team/production use.
  # Uncomment and configure for your backend of choice.
  # backend "s3" {
  #   bucket         = "interview-helper-tfstate"
  #   key            = "prod/terraform.tfstate"
  #   region         = "eu-north-1"
  #   dynamodb_table = "interview-helper-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "interview-helper"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
