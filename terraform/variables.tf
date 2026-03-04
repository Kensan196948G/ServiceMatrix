variable "aws_region" {
  description = "AWS リージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "デプロイ環境 (dev/staging/prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment は dev, staging, prod のいずれかである必要があります。"
  }
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "servicematrix"
}

variable "vpc_cidr" {
  description = "VPC CIDR ブロック"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "使用するアベイラビリティーゾーン"
  type        = list(string)
  default     = ["ap-northeast-1a", "ap-northeast-1c"]
}

variable "ecs_task_cpu" {
  description = "ECS タスク CPU (vCPU x 1024)"
  type        = number
  default     = 256
}

variable "ecs_task_memory" {
  description = "ECS タスク メモリ (MiB)"
  type        = number
  default     = 512
}

variable "ecs_desired_count" {
  description = "ECS サービス希望タスク数"
  type        = number
  default     = 1
}

variable "rds_instance_class" {
  description = "RDS インスタンスクラス"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS ストレージ容量 (GB)"
  type        = number
  default     = 20
}

variable "backend_image" {
  description = "バックエンド Docker イメージ URI"
  type        = string
  default     = "ghcr.io/kensan196948g/servicematrix-backend:latest"
}

variable "domain_name" {
  description = "アプリケーションのドメイン名（CloudFront用）"
  type        = string
  default     = ""
}

variable "db_username" {
  description = "RDS データベースユーザー名"
  type        = string
  default     = "servicematrix"
  sensitive   = true
}

variable "db_password" {
  description = "RDS データベースパスワード"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "RDS データベース名"
  type        = string
  default     = "servicematrix"
}

variable "certificate_arn" {
  description = "HTTPS リスナー用 ACM 証明書 ARN"
  type        = string
  default     = ""
}
