resource "aws_iam_user" "ci" {
  name = "${var.project_name}-ci"
}

resource "aws_iam_access_key" "ci" {
  user = aws_iam_user.ci.name
}

data "aws_iam_policy_document" "ci_ecr" {
  statement {
    sid    = "ECRAuth"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECRPushPull"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:ListImages",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [
      aws_ecr_repository.api.arn,
      aws_ecr_repository.frontend.arn,
    ]
  }
}

data "aws_iam_policy_document" "ci_eks" {
  statement {
    sid    = "EKSDescribe"
    effect = "Allow"
    actions = [
      "eks:DescribeCluster",
    ]
    resources = [
      "arn:aws:eks:${var.aws_region}:${var.aws_account_id}:cluster/*",
    ]
  }
}

resource "aws_iam_user_policy" "ci_ecr" {
  name   = "${var.project_name}-ci-ecr"
  user   = aws_iam_user.ci.name
  policy = data.aws_iam_policy_document.ci_ecr.json
}

resource "aws_iam_user_policy" "ci_eks" {
  name   = "${var.project_name}-ci-eks"
  user   = aws_iam_user.ci.name
  policy = data.aws_iam_policy_document.ci_eks.json
}

data "aws_iam_policy_document" "ci_terraform" {
  statement {
    sid    = "TerraformStateS3"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      "arn:aws:s3:::cms-fraud-terraform-state",
      "arn:aws:s3:::cms-fraud-terraform-state/*",
    ]
  }

  statement {
    sid    = "TerraformStateLock"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
    ]
    resources = [
      "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/cms-fraud-terraform-locks",
    ]
  }

  statement {
    sid    = "TerraformManageResources"
    effect = "Allow"
    actions = [
      "ecr:CreateRepository",
      "ecr:DeleteRepository",
      "ecr:DescribeRepositories",
      "ecr:ListTagsForResource",
      "ecr:TagResource",
      "ecr:UntagResource",
      "ecr:PutLifecyclePolicy",
      "ecr:GetLifecyclePolicy",
      "ecr:DeleteLifecyclePolicy",
      "ecr:PutImageScanningConfiguration",
      "ecr:SetRepositoryPolicy",
      "ecr:GetRepositoryPolicy",
      "ecr:DeleteRepositoryPolicy",
      "iam:CreateUser",
      "iam:DeleteUser",
      "iam:GetUser",
      "iam:ListUserTags",
      "iam:TagUser",
      "iam:UntagUser",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
      "iam:ListAccessKeys",
      "iam:PutUserPolicy",
      "iam:GetUserPolicy",
      "iam:DeleteUserPolicy",
      "iam:ListUserPolicies",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_user_policy" "ci_terraform" {
  name   = "${var.project_name}-ci-terraform"
  user   = aws_iam_user.ci.name
  policy = data.aws_iam_policy_document.ci_terraform.json
}
