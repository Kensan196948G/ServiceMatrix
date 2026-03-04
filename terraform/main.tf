# ServiceMatrix - AWS インフラストラクチャ定義
# ITIL 4 / J-SOX 準拠 本番グレードインフラ

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix        = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  tags               = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix       = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage
  db_username       = var.db_username
  db_password       = var.db_password
  tags              = local.common_tags

  depends_on = [module.vpc]
}

module "ecs" {
  source = "./modules/ecs"

  name_prefix       = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  public_subnet_ids = module.vpc.public_subnet_ids
  task_cpu          = var.ecs_task_cpu
  task_memory       = var.ecs_task_memory
  desired_count     = var.ecs_desired_count
  backend_image     = var.backend_image
  database_url      = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${module.rds.endpoint}/servicematrix"
  tags              = local.common_tags

  depends_on = [module.vpc, module.rds]
}

module "cloudfront" {
  source = "./modules/cloudfront"

  name_prefix  = local.name_prefix
  alb_dns_name = module.ecs.alb_dns_name
  domain_name  = var.domain_name
  tags         = local.common_tags

  depends_on = [module.ecs]
}
