# FinBot Enterprise - Infrastructure as Code

## Terraform Configuration for AWS

This directory contains Terraform configurations for deploying FinBot Enterprise on AWS.

### Prerequisites
- Terraform >= 1.5.0
- AWS CLI configured
- Python 3.11+

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Global Accelerator                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Application Load Balancer               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   API Gateway │    │  Auth Service │    │  ML Service   │
│     (EKS)     │    │     (EKS)     │    │    (EKS)      │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ PostgreSQL  │  │   Redis     │  │  ClickHouse │         │
│  │ (RDS)       │  │  (ElastiCache)│ │ (MSK/Kafka) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
infrastructure/
├── terraform/
│   ├── main.tf              # Main configuration
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   ├── providers.tf         # Provider configurations
│   ├── vpc.tf               # VPC and networking
│   ├── eks.tf               # EKS cluster
│   ├── rds.tf               # RDS databases
│   ├── elasticache.tf       # Redis cluster
│   ├── msk.tf               # Kafka (MSK)
│   ├── iam.tf               # IAM roles and policies
│   └── monitoring.tf        # CloudWatch, Prometheus
├── k8s/
│   ├── namespaces.yaml      # Kubernetes namespaces
│   ├── api-gateway/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── auth-service/
│   ├── ml-service/
│   └── data-ingestion/
└── monitoring/
    ├── prometheus-values.yaml
    ├── grafana-values.yaml
    └── alertmanager-rules.yaml
```

### Quick Start

#### 1. Initialize Terraform
```bash
cd infrastructure/terraform
terraform init
```

#### 2. Create tfvars file
```bash
cp example.tfvars production.tfvars
# Edit production.tfvars with your values
```

#### 3. Plan and Apply
```bash
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars
```

#### 4. Configure kubectl
```bash
aws eks update-kubeconfig --region us-east-1 --name finbot-cluster
```

#### 5. Deploy Kubernetes resources
```bash
kubectl apply -f ../k8s/namespaces.yaml
kubectl apply -f ../k8s/api-gateway/
kubectl apply -f ../k8s/auth-service/
kubectl apply -f ../k8s/ml-service/
```

### Key Resources

| Resource | Type | Purpose |
|----------|------|---------|
| finbot-vpc | VPC | Isolated network environment |
| finbot-eks | EKS | Kubernetes cluster |
| finbot-rds | RDS PostgreSQL | Primary database |
| finbot-redis | ElastiCache | Caching layer |
| finbot-msk | MSK Kafka | Event streaming |
| finbot-alb | ALB | Load balancing |

### Cost Optimization

- Use Spot Instances for worker nodes (70% savings)
- Auto-scaling based on metrics
- Reserved Instances for databases
- S3 Intelligent Tiering for storage

### Security

- All resources in private subnets
- Security groups with minimal access
- IAM roles with least privilege
- Encryption at rest and in transit
- WAF for DDoS protection

### Monitoring & Alerting

- CloudWatch for AWS metrics
- Prometheus for application metrics
- Grafana for visualization
- PagerDuty integration for alerts

### Disaster Recovery

- Multi-AZ deployment
- Daily automated backups
- Point-in-time recovery enabled
- Cross-region replication for critical data

### Estimated Monthly Costs (Production)

| Component | Cost |
|-----------|------|
| EKS Cluster + Nodes | $2,500 |
| RDS PostgreSQL | $800 |
| ElastiCache Redis | $400 |
| MSK Kafka | $600 |
| Data Transfer | $300 |
| Monitoring & Logging | $200 |
| **Total** | **~$4,800/month** |

---

*For detailed configuration examples, see individual .tf files.*
