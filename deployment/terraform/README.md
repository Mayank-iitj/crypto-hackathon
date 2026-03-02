# Q-Shield Terraform Deployment Guide

This directory contains Terraform configurations for deploying Q-Shield to AWS production infrastructure.

## Architecture

The Terraform configuration creates the following AWS infrastructure:

### Networking
- **VPC** with public and private subnets across 2 availability zones
- **Internet Gateway** for external connectivity
- **NAT Gateways** for outbound traffic from private subnets
- **Security Groups** for EKS, RDS, and Redis

### Compute
- **EKS Cluster** (Elastic Kubernetes Service) with version 1.28+
- **Auto Scaling Node Group** with 2-10 nodes (configurable)
- **EC2 Instances** using t3.large/xlarge instance types

### Data
- **RDS PostgreSQL 16** for application database
- **ElastiCache Redis 7** for caching and message queue
- **S3 Bucket** for application assets and backups
- **CloudFront** distribution for CDN

### Monitoring
- **CloudWatch** logs and metrics
- **VPC Flow Logs** for network monitoring
- **RDS Enhanced Monitoring**

## Prerequisites

### Local Tools
```bash
# Terraform
terraform version  # >= 1.0

# AWS CLI
aws --version     # v2.x

# kubectl
kubectl version   # 1.28+

# helm (optional, for Helm charts)
helm version      # 3.x+
```

### AWS Permissions
Required IAM permissions:
- EC2 (VPC, Subnets, Security Groups, NAT Gateways)
- EKS (Cluster, Node Groups)
- RDS (Database Instance, Parameter Groups)
- ElastiCache (Cluster, Parameter Groups)
- IAM (Roles, Policies)
- S3 (Buckets, Versioning)
- CloudFront (Distributions)
- CloudWatch (Logs)

### AWS Account Setup

```bash
# Configure AWS credentials
aws configure
# OR
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Verify credentials
aws sts get-caller-identity
```

### Terraform State Backend

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket qshield-terraform-state \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket qshield-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket qshield-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state lock
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

## Deployment Steps

### 1. Initialize Terraform

```bash
cd deployment/terraform

# Initialize workspace
terraform init
```

### 2. Configure Variables

```bash
# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required Variables:**
```hcl
aws_account_id = "123456789012"        # Your AWS account ID
environment    = "production"          # Environment name
db_password    = "strong-password"     # RDS master password
domain_name    = "yourdomain.com"      # Your domain
```

### 3. Validate Configuration

```bash
# Format check
terraform fmt -check -recursive

# Syntax validation
terraform validate

# Security check (install tfsec first)
tfsec .

# Cost estimation
terraform plan -out=tfplan
terraform show -json tfplan | jq '.resource_changes | length'
```

### 4. Plan Deployment

```bash
# Preview changes
terraform plan -out=tfplan

# Review output carefully
terraform show tfplan
```

### 5. Apply Configuration

```bash
# Deploy infrastructure
terraform apply tfplan

# Wait 10-15 minutes for EKS cluster creation
```

### 6. Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region $(terraform output -raw aws_region) \
  --name $(terraform output -raw eks_cluster_name)

# Verify cluster access
kubectl get nodes

# Expected output: 3 nodes in NotReady state (they're initializing)
```

### 7. Deploy to Kubernetes

```bash
# Navigate to Kubernetes manifests
cd ../../deployment/kubernetes

# Create namespace and secrets
kubectl apply -f qshield-k8s-production.yaml

# Verify deployments
kubectl get pods -n qshield
kubectl get svc -n qshield

# Check logs
kubectl logs -n qshield -l app=qshield-api -f
```

### 8. Verify Deployment

```bash
# Get API service endpoint
kubectl get svc -n qshield qshield-api

# Port forward for testing
kubectl port-forward -n qshield svc/qshield-api 8000:8000

# Test API
curl http://localhost:8000/health

# Check database connectivity
kubectl exec -it -n qshield deployment/qshield-api -- \
  psql postgresql://qshield@postgres.qshield.svc.cluster.local/qshield -c "SELECT 1"
```

## Management & Operations

### Viewing Outputs

```bash
# All outputs
terraform output

# Specific output
terraform output eks_cluster_endpoint

# JSON format
terraform output -json
```

### Scaling

```bash
# Scale node group
terraform apply -var "desired_capacity=5"

# Update instance types
terraform apply -var 'instance_types=["t3.xlarge"]'
```

### Updating Services

```bash
# Update Kubernetes version
terraform apply -var "kubernetes_version=1.29"

# Update RDS instance class
terraform apply -var "db_instance_class=db.t4g.large"

# Update Redis nodes
terraform apply -var "redis_num_nodes=3"
```

### Destroying Infrastructure

```bash
# Plan destruction
terraform plan -destroy

# Destroy all resources
terraform destroy

# Destroy specific resource
terraform destroy -target aws_db_instance.main
```

## Troubleshooting

### State Lock Issues

```bash
# View lock information
aws dynamodb scan --table-name terraform-lock

# Force unlock (be careful!)
terraform force-unlock <LOCK_ID>
```

### EKS Cluster Issues

```bash
# Check cluster status
aws eks describe-cluster --name <cluster-name>

# View cluster logs
aws logs tail /aws/eks/<cluster-name>/cluster

# Describe node group
aws eks describe-nodegroup --cluster-name <cluster-name> --nodegroup-name <nodegroup-name>
```

### RDS Connectivity

```bash
# Connect to RDS from EKS pod
kubectl run -it --rm debug --image=postgres:16 --restart=Never -n qshield -- \
  psql -h postgres.qshield.svc.cluster.local -U qshield -d qshield

# Alternative: Use Parameter Store
aws ssm put-parameter --name /qshield/db-password --value "password" --type SecureString
```

### Terraform Issues

```bash
# Enable debug logging
export TF_LOG=DEBUG

# Import existing resource
terraform import aws_eks_cluster.main qshield-production

# Refresh state
terraform refresh
```

## Security Best Practices

1. **State File Protection**
   - Store in encrypted S3 bucket ✓ (configured)
   - Enable versioning ✓ (configured)
   - Use DynamoDB locking ✓ (configured)
   - Never commit tfstate to git

2. **Network Security**
   - RDS in private subnets only
   - Redis in private subnets only
   - EKS API endpoint with restricted CIDR
   - Security groups with least-privilege access

3. **Database Security**
   - RDS encryption at rest
   - Multi-AZ deployment for HA
   - Automated backups (30 days)
   - IAM database authentication (optional)

4. **Access Control**
   - EKS RBAC configured
   - Pod security policies
   - Network policies
   - Service accounts with least permissions

5. **Monitoring & Logging**
   - CloudWatch logging enabled
   - VPC Flow Logs enabled
   - RDS Enhanced Monitoring
   - CloudTrail (for audit)

## Cost Estimation

```bash
# Install Infracost
curl https://oss.infracost.io/downloads/linux/infracost

# Estimate costs
infracost breakdown --path tfplan --format table
```

**Estimated Monthly Cost (production):**
- EKS Cluster: ~$73
- EC2 Nodes (3x t3.large): ~$180
- RDS (db.t4g.medium multi-AZ): ~$150
- Redis (2x cache.t4g.micro): ~$30
- S3 + CloudFront: ~$20
- **Total: ~$450/month** (excluding data transfer)

## Support & Maintenance

### Regular Maintenance Tasks

```bash
# Monthly: Update Terraform provider versions
terraform init -upgrade

# Quarterly: Review and update resource configurations
terraform plan

# Annually: Review and optimize costs
terraform plan -var "environment=production"
```

### Emergency Procedures

```bash
# Backup current state
aws s3 cp s3://qshield-terraform-state/prod/terraform.tfstate ./backup.tfstate

# Restore from backup
aws s3 cp ./backup.tfstate s3://qshield-terraform-state/prod/terraform.tfstate
```

## Additional Resources

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Kubernetes Security Documentation](https://kubernetes.io/docs/concepts/security/)
- [Terraform Best Practices](https://www.terraform.io/cloud-docs/recommended-practices)
