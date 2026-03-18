terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "cms-fraud-terraform-state"
    key            = "cms-fraud-detection/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "cms-fraud-terraform-locks"
    encrypt        = true
  }
}
