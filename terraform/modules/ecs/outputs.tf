output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "service_name" {
  value = aws_ecs_service.backend.name
}

output "ecs_security_group_id" {
  description = "ECS タスクのセキュリティグループ ID (参照用)"
  value       = var.ecs_sg_id
}
