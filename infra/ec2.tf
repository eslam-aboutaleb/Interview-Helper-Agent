# Application server: EC2 instance running the Docker Compose stack.

data "aws_ssm_parameter" "amazon_linux_2023" {
  name = "/aws/service/ami-amazon-linux-latest/amazon-linux-2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.amazon_linux_2023.value
  instance_type          = var.instance_type
  key_name               = var.key_name != "" ? var.key_name : null
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  user_data = base64encode(templatefile("${path.module}/user-data.sh.tftpl", {
    repo_url            = var.repo_url
    repo_branch         = var.repo_branch
    database_url        = var.use_rds ? "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main[0].address}:5432/${var.db_name}" : "postgresql://${var.db_username}:${var.db_password}@db:5432/${var.db_name}"
    db_name             = var.db_name
    db_user             = var.db_username
    db_password         = var.db_password
    gemini_api_key      = var.gemini_api_key
    cors_origins        = var.cors_origins
    log_level           = var.log_level
    environment         = var.environment
    llm_model           = var.llm_model
    llm_fallback_models = var.llm_fallback_models
    use_rds             = var.use_rds
  }))

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-app"
  }

  # When using RDS, wait until the database is available
  # before booting the application stack. With use_rds = false
  # the resource has count = 0, making this a no-op.
  depends_on = [aws_db_instance.main]
}
