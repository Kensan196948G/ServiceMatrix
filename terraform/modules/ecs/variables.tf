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

variable "database_url" {
  type      = string
  sensitive = true
}

variable "tags" {
  type = map(string)
}
