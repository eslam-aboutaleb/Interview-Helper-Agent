# Outputs for the deployed infrastructure.

output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main.id
}

output "ec2_instance_id" {
  description = "ID of the application EC2 instance"
  value       = aws_instance.app.id
}

output "ec2_public_ip" {
  description = "Public IP of the application server"
  value       = aws_instance.app.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the application server"
  value       = aws_instance.app.public_dns
}

output "frontend_url" {
  description = "URL of the frontend application"
  value       = "http://${aws_instance.app.public_dns}"
}

output "backend_api_url" {
  description = "URL of the backend API (proxied through the frontend Nginx on /api)"
  value       = "http://${aws_instance.app.public_dns}/api"
}

output "api_docs_url" {
  description = "URL of the interactive API documentation (proxied through the frontend Nginx)"
  value       = "http://${aws_instance.app.public_dns}/docs"
}

output "rds_endpoint" {
  description = "Endpoint of the RDS instance (only when use_rds = true)"
  value       = var.use_rds ? aws_db_instance.main[0].address : null
}

output "ssm_command" {
  description = "Command to open an SSM session on the instance (no SSH key needed)"
  value       = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.aws_region}"
}
