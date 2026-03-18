#!/usr/bin/env bash
# Bootstrap Terraform state backend (run once, before terraform init)
# Creates S3 bucket + DynamoDB table for remote state locking.
set -euo pipefail

PROFILE="precise-eng"
REGION="us-east-1"
BUCKET="cms-fraud-terraform-state"
TABLE="cms-fraud-terraform-locks"

echo "Creating S3 bucket: ${BUCKET}"
aws s3api create-bucket \
  --bucket "${BUCKET}" \
  --region "${REGION}" \
  --profile "${PROFILE}" 2>/dev/null || echo "  Bucket already exists"

aws s3api put-bucket-versioning \
  --bucket "${BUCKET}" \
  --versioning-configuration Status=Enabled \
  --profile "${PROFILE}"

aws s3api put-bucket-encryption \
  --bucket "${BUCKET}" \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }' \
  --profile "${PROFILE}"

aws s3api put-public-access-block \
  --bucket "${BUCKET}" \
  --public-access-block-configuration '{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }' \
  --profile "${PROFILE}"

echo "Creating DynamoDB table: ${TABLE}"
aws dynamodb create-table \
  --table-name "${TABLE}" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "${REGION}" \
  --profile "${PROFILE}" 2>/dev/null || echo "  Table already exists"

echo "Bootstrap complete. Run: cd terraform && terraform init"
