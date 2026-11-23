data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  log_group_name = "/${var.name}/watchdog"

  config_yaml = yamlencode({
    check_interval          = var.check_interval
    timeout                 = 10
    failure_threshold       = 2
    tls_expiry_warning_days = 14
    history_file            = "logs/history.csv"
    targets                 = var.targets
  })
}

# ---------------------------------------------------------------- alerting

resource "aws_sns_topic" "alerts" {
  name = "${var.name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------------------------------------------------------------- logging

resource "aws_cloudwatch_log_group" "watchdog" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
}

# Count failed checks so they can be graphed and alarmed on in CloudWatch.
resource "aws_cloudwatch_log_metric_filter" "down_checks" {
  name           = "${var.name}-down-checks"
  log_group_name = aws_cloudwatch_log_group.watchdog.name
  pattern        = "\"status=DOWN\""

  metric_transformation {
    namespace     = "ServiceWatchdog"
    name          = "DownChecks"
    value         = "1"
    default_value = "0"
  }
}

# Count every check (any status) as a heartbeat for the watchdog itself.
resource "aws_cloudwatch_log_metric_filter" "checks" {
  name           = "${var.name}-checks"
  log_group_name = aws_cloudwatch_log_group.watchdog.name
  pattern        = "\"status=\""

  metric_transformation {
    namespace     = "ServiceWatchdog"
    name          = "Checks"
    value         = "1"
    default_value = "0"
  }
}

# Who watches the watchdog: alert if no checks are logged for 3 intervals.
resource "aws_cloudwatch_metric_alarm" "watchdog_silent" {
  alarm_name          = "${var.name}-silent"
  alarm_description   = "service-watchdog has not logged any checks - the monitor itself may be down."
  namespace           = "ServiceWatchdog"
  metric_name         = "Checks"
  statistic           = "Sum"
  period              = var.check_interval * 60 * 3
  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# ---------------------------------------------------------------- IAM

data "aws_iam_policy_document" "assume_ec2" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "watchdog" {
  name               = "${var.name}-instance"
  assume_role_policy = data.aws_iam_policy_document.assume_ec2.json
}

# Shell access through SSM Session Manager instead of SSH keys and open ports.
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.watchdog.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Least privilege: write to one log group and publish to one topic, nothing else.
data "aws_iam_policy_document" "watchdog" {
  statement {
    sid       = "ShipLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
    resources = ["${aws_cloudwatch_log_group.watchdog.arn}:*"]
  }

  statement {
    sid       = "PublishAlerts"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]
  }
}

resource "aws_iam_role_policy" "watchdog" {
  name   = "${var.name}-least-privilege"
  role   = aws_iam_role.watchdog.id
  policy = data.aws_iam_policy_document.watchdog.json
}

resource "aws_iam_instance_profile" "watchdog" {
  name = "${var.name}-instance"
  role = aws_iam_role.watchdog.name
}

# ---------------------------------------------------------------- network

resource "aws_security_group" "watchdog" {
  name_prefix = "${var.name}-"
  description = "service-watchdog: no inbound access, outbound only for health checks"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Health checks may target any host and port"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------- compute

resource "aws_instance" "watchdog" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.instance_type
  subnet_id                   = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids      = [aws_security_group.watchdog.id]
  iam_instance_profile        = aws_iam_instance_profile.watchdog.name
  associate_public_ip_address = true

  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    repo_url      = var.repo_url
    repo_ref      = var.repo_ref
    region        = var.region
    sns_topic_arn = aws_sns_topic.alerts.arn
    log_group     = aws_cloudwatch_log_group.watchdog.name
    config_yaml   = local.config_yaml
  })
  user_data_replace_on_change = true

  tags = {
    Name = var.name
  }

  lifecycle {
    # Patch in place (dnf upgrade) instead of replacing the instance on every new AMI release
    ignore_changes = [ami]
  }
}

# Automatically recover the instance onto healthy hardware if AWS detects a host failure.
resource "aws_cloudwatch_metric_alarm" "instance_recover" {
  alarm_name          = "${var.name}-instance-recover"
  alarm_description   = "Recover the watchdog instance when the underlying host fails."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_System"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  dimensions          = { InstanceId = aws_instance.watchdog.id }
  alarm_actions       = ["arn:aws:automate:${var.region}:ec2:recover", aws_sns_topic.alerts.arn]
}

# ---------------------------------------------------------------- dashboard

resource "aws_cloudwatch_dashboard" "watchdog" {
  dashboard_name = var.name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Failed checks"
          region  = var.region
          stat    = "Sum"
          period  = 300
          metrics = [["ServiceWatchdog", "DownChecks"]]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Checks performed (watchdog heartbeat)"
          region  = var.region
          stat    = "Sum"
          period  = 300
          metrics = [["ServiceWatchdog", "Checks"]]
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 8
        properties = {
          title  = "Recent failures"
          region = var.region
          query  = "SOURCE '${aws_cloudwatch_log_group.watchdog.name}' | fields @timestamp, @message | filter @message like /status=(DOWN|DEGRADED)/ | sort @timestamp desc | limit 50"
          view   = "table"
        }
      },
    ]
  })
}
