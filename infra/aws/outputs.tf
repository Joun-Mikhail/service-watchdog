output "instance_id" {
  description = "EC2 instance running service-watchdog."
  value       = aws_instance.watchdog.id
}

output "sns_topic_arn" {
  description = "SNS topic receiving alerts."
  value       = aws_sns_topic.alerts.arn
}

output "log_group" {
  description = "CloudWatch log group with the watchdog logs."
  value       = aws_cloudwatch_log_group.watchdog.name
}

output "connect_command" {
  description = "Open a shell on the instance through SSM Session Manager (no SSH needed)."
  value       = "aws ssm start-session --target ${aws_instance.watchdog.id} --region ${var.region}"
}

output "tail_logs_command" {
  description = "Stream the watchdog logs from CloudWatch."
  value       = "aws logs tail ${aws_cloudwatch_log_group.watchdog.name} --follow --region ${var.region}"
}
