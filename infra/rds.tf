# Optional managed PostgreSQL database.
# Provisioned only when use_rds = true; otherwise the
# application runs a containerized postgres via Compose.

resource "aws_db_subnet_group" "main" {
  count      = var.use_rds ? 1 : 0
  name       = "${var.project_name}-${var.environment}"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  count = var.use_rds ? 1 : 0

  identifier             = "${var.project_name}-${var.environment}"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp3"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = [aws_security_group.rds[0].id]

  # Production hardening: enable automated backups.
  backup_retention_period    = 7
  backup_window              = "03:00-04:00"
  maintenance_window         = "sun:04:00-sun:05:00"
  auto_minor_version_upgrade = true
  publicly_accessible        = false
  storage_encrypted          = true

  # Set to false and add final_snapshot_identifier for real production
  # workloads so the database is not destroyed on `terraform destroy`.
  skip_final_snapshot = true

  tags = {
    Name = "${var.project_name}-${var.environment}-db"
  }
}
