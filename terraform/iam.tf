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
    resources = [aws_ecr_repository.api.arn]
  }
}

resource "aws_iam_user_policy" "ci_ecr" {
  name   = "${var.project_name}-ci-ecr"
  user   = aws_iam_user.ci.name
  policy = data.aws_iam_policy_document.ci_ecr.json
}
