# Security groups for the application EC2 and (optional) RDS.

resource "aws_security_group" "ec2" {
  name_prefix = "${var.project_name}-ec2-"
  description = "Application server: HTTP(S) frontend; the API is proxied through it"
  vpc_id      = aws_vpc.main.id

  # SSH is opt-in: leave allowed_ssh_cidr empty (the default) and
  # administer the instance over SSM instead.
  dynamic "ingress" {
    for_each = var.allowed_ssh_cidr != "" ? [var.allowed_ssh_cidr] : []
    content {
      description = "SSH administration"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  ingress {
    description = "Frontend HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Frontend HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # The backend API on port 8000 is intentionally NOT exposed:
  # the Nginx frontend proxies /api/ to it over the Compose network.

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ec2-sg"
  }
}

resource "aws_security_group" "rds" {
  count       = var.use_rds ? 1 : 0
  name_prefix = "${var.project_name}-rds-"
  description = "PostgreSQL: reachable only from the application server"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from the app server"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}
