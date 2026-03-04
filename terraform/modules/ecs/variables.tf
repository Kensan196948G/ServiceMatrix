variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "task_cpu" {
  type = number
}

variable "task_memory" {
  type = number
}

variable "desired_count" {
  type = number
}

variable "backend_image" {
  type = string
}

variable "database_url_ssm_arn" {
  description = "SSM Parameter Store ARN for DATABASE_URL (SecureString)"
  type        = string
}

variable "certificate_arn" {
  description = "ACM 証明書 ARN (HTTPS リスナー用)"
  type        = string
  default     = ""
}

variable "ecs_sg_id" {
  description = "ルートモジュールで作成された ECS タスクセキュリティグループ ID (循環依存回避)"
  type        = string
}

variable "tags" {
  type = map(string)
}
