# FinBot Enterprise - Main Terraform Configuration

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "s3" {
    bucket = "finbot-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
    
    dynamodb_table = "finbot-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "FinBot"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "finbot-vpc"
  cidr = var.vpc_cidr
  
  azs             = var.availability_zones
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs
  
  enable_nat_gateway   = true
  single_nat_gateway   = false
  one_nat_gateway_per_az = true
  
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "finbot-vpc"
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "finbot-cluster"
  cluster_version = "1.28"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  eks_managed_node_groups = {
    primary = {
      min_size     = 3
      max_size     = 10
      desired_size = 5
      
      instance_types = ["m6i.xlarge"]
      disk_size      = 100
      
      update_config = {
        max_unavailable_percentage = 33
      }
    }
    
    spot_nodes = {
      min_size     = 2
      max_size     = 8
      desired_size = 4
      
      instance_types = ["m6i.large", "m5.large", "m5a.large"]
      capacity_type  = "SPOT"
      disk_size      = 50
    }
  }
  
  tags = {
    Name = "finbot-eks"
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "finbot_db" {
  identifier = "finbot-postgres"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.large"
  
  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true
  
  db_name  = "finbot"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.finbot.name
  
  multi_az               = true
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  auto_minor_version_upgrade = true
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "finbot-final-snapshot"
  
  performance_insights_enabled = true
  monitoring_interval          = 60
  
  tags = {
    Name = "finbot-postgres"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "finbot_redis" {
  cluster_id           = "finbot-redis"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 3
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  security_group_ids = [aws_security_group.redis_sg.id]
  subnet_group_name  = aws_elasticache_subnet_group.finbot.name
  
  snapshot_retention_limit = 7
  snapshot_window          = "02:00-03:00"
  maintenance_window       = "Mon:03:00-Mon:04:00"
  
  tags = {
    Name = "finbot-redis"
  }
}

# Security Groups
resource "aws_security_group" "rds_sg" {
  name        = "finbot-rds-sg"
  description = "Security group for RDS"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "finbot-rds-sg"
  }
}

resource "aws_security_group" "redis_sg" {
  name        = "finbot-redis-sg"
  description = "Security group for Redis"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "finbot-redis-sg"
  }
}

# Subnet Groups
resource "aws_db_subnet_group" "finbot" {
  name       = "finbot-db-subnet"
  subnet_ids = module.vpc.private_subnets
  
  tags = {
    Name = "finbot-db-subnet"
  }
}

resource "aws_elasticache_subnet_group" "finbot" {
  name       = "finbot-redis-subnet"
  subnet_ids = module.vpc.private_subnets
  
  tags = {
    Name = "finbot-redis-subnet"
  }
}

# S3 Bucket for artifacts
resource "aws_s3_bucket" "finbot_artifacts" {
  bucket = "finbot-artifacts-${var.environment}"
  
  tags = {
    Name = "finbot-artifacts"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "finbot_artifacts" {
  bucket = aws_s3_bucket.finbot_artifacts.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "finbot_logs" {
  name              = "/aws/finbot/${var.environment}"
  retention_in_days = 90
  
  tags = {
    Name = "finbot-logs"
  }
}
