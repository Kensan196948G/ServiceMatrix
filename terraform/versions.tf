terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    # terraform init -backend-config="bucket=<your-bucket>" で設定
    # bucket = "servicematrix-terraform-state"
    # key    = "servicematrix/terraform.tfstate"
    # region = "ap-northeast-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ServiceMatrix"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
