output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS 名"
  value       = module.ecs.alb_dns_name
}

output "cloudfront_domain_name" {
  description = "CloudFront ディストリビューション ドメイン名"
  value       = module.cloudfront.domain_name
}

output "rds_endpoint" {
  description = "RDS エンドポイント"
  value       = module.rds.endpoint
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS クラスター名"
  value       = module.ecs.cluster_name
}
