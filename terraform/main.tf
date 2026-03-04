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

# ECS セキュリティグループを先に作成し、RDS 最小権限 SG 参照の循環依存を回避
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${local.name_prefix}-ecs-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-sg" })

  depends_on = [module.vpc]
}

module "rds" {
  source = "./modules/rds"

  name_prefix           = local.name_prefix
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnet_ids
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  db_username           = var.db_username
  db_password           = var.db_password
  ecs_security_group_id = aws_security_group.ecs_tasks.id
  tags                  = local.common_tags

  depends_on = [module.vpc, aws_security_group.ecs_tasks]
}

resource "aws_ssm_parameter" "database_url" {
  name  = "/${var.project_name}/${var.environment}/database_url"
  type  = "SecureString"
  value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${module.rds.endpoint}/${module.rds.db_name}"

  tags = local.common_tags

  depends_on = [module.rds]
}

module "ecs" {
  source = "./modules/ecs"

  name_prefix          = local.name_prefix
  vpc_id               = module.vpc.vpc_id
  subnet_ids           = module.vpc.private_subnet_ids
  public_subnet_ids    = module.vpc.public_subnet_ids
  task_cpu             = var.ecs_task_cpu
  task_memory          = var.ecs_task_memory
  desired_count        = var.ecs_desired_count
  backend_image        = var.backend_image
  database_url_ssm_arn = aws_ssm_parameter.database_url.arn
  certificate_arn      = var.certificate_arn
  ecs_sg_id            = aws_security_group.ecs_tasks.id
  tags                 = local.common_tags

  depends_on = [module.vpc, module.rds, aws_ssm_parameter.database_url]
}

module "cloudfront" {
  source = "./modules/cloudfront"

  name_prefix  = local.name_prefix
  alb_dns_name = module.ecs.alb_dns_name
  domain_name  = var.domain_name
  tags         = local.common_tags

  depends_on = [module.ecs]
}
