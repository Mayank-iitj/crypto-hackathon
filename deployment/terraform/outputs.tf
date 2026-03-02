# Terraform Outputs for Q-Shield Production Deployment

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = aws_eks_cluster.main.endpoint
  sensitive   = false
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_version" {
  description = "EKS cluster version"
  value       = aws_eks_cluster.main.version
}

output "eks_cluster_ca_certificate" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_security_group.eks.id
}

output "eks_node_group_id" {
  description = "EKS node group ID"
  value       = aws_eks_node_group.main.id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (use with :5432 port)"
  value       = aws_db_instance.main.endpoint
  sensitive   = false
}

output "rds_resource_id" {
  description = "RDS resource ID"
  value       = aws_db_instance.main.resource_id
  sensitive   = false
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_master_username" {
  description = "RDS master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint address"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
  sensitive   = false
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_cluster.main.port
}

output "redis_cluster_id" {
  description = "ElastiCache cluster ID"
  value       = aws_elasticache_cluster.main.cluster_id
}

output "s3_bucket_name" {
  description = "S3 bucket name for application assets"
  value       = aws_s3_bucket.app.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.app.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

# Kubernetes Configuration

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}

output "kubernetes_context" {
  description = "Kubernetes context name"
  value       = "arn:aws:eks:${var.aws_region}:${var.aws_account_id}:cluster/${aws_eks_cluster.main.name}"
}

# Connection Information

output "postgres_connection_string" {
  description = "PostgreSQL connection string"
  value       = "postgresql://qshield:PASSWORD@${aws_db_instance.main.endpoint}/qshield"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://:PASSWORD@${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.port}/0"
  sensitive   = true
}

# Deployment Information

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    environment     = var.environment
    region          = var.aws_region
    vpc_cidr        = aws_vpc.main.cidr_block
    eks_cluster     = aws_eks_cluster.main.name
    eks_version     = aws_eks_cluster.main.version
    rds_instance    = aws_db_instance.main.identifier
    redis_cluster   = aws_elasticache_cluster.main.cluster_id
    s3_bucket       = aws_s3_bucket.app.bucket
    domain          = var.domain_name
  }
}
