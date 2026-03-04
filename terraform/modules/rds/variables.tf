variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "instance_class" {
  type = string
}

variable "allocated_storage" {
  type = number
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "ecs_security_group_id" {
  description = "ECS タスクのセキュリティグループ ID (最小権限アクセス制御)"
  type        = string
}

variable "tags" {
  type = map(string)
}
