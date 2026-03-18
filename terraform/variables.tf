variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "cms-fraud-detection"
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
  default     = "376567172837"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "precise-eng"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "github_repo" {
  description = "GitHub repository (org/repo format)"
  type        = string
  default     = "precisesoft/cms-fraud-detection"
}
