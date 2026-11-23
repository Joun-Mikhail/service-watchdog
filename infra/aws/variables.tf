variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-central-1"
}

variable "name" {
  description = "Name prefix for all resources."
  type        = string
  default     = "service-watchdog"
}

variable "alert_email" {
  description = "Email address subscribed to the SNS alert topic (confirm the subscription email after apply)."
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}

variable "instance_type" {
  description = "EC2 instance type. t3.micro is free-tier eligible in most regions."
  type        = string
  default     = "t3.micro"
}

variable "repo_url" {
  description = "Git repository the instance installs service-watchdog from."
  type        = string
  default     = "https://github.com/Joun-Mikhail/service-watchdog.git"
}

variable "repo_ref" {
  description = "Branch or tag of the repository to deploy."
  type        = string
  default     = "main"
}

variable "targets" {
  description = "Targets to monitor, in the same format as config.yaml (plain URLs or objects)."
  type        = any
  default = [
    { name = "Example", url = "https://example.com", keyword = "Example Domain", max_latency_ms = 2000 },
    "https://www.google.com",
  ]
}

variable "check_interval" {
  description = "Minutes between check rounds."
  type        = number
  default     = 5
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps the watchdog logs."
  type        = number
  default     = 14
}
