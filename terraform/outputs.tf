output "ecr_repository_url" {
  description = "ECR repository URL for backend image"
  value       = aws_ecr_repository.api.repository_url
}

output "ci_user_arn" {
  description = "ARN of the CI/CD IAM user"
  value       = aws_iam_user.ci.arn
}

output "ci_user_access_key_id" {
  description = "Access key ID for CI/CD user"
  value       = aws_iam_access_key.ci.id
  sensitive   = true
}

output "ci_user_secret_access_key" {
  description = "Secret access key for CI/CD user"
  value       = aws_iam_access_key.ci.secret
  sensitive   = true
}
