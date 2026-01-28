# AlgoTrading Application - AWS Deployment Guide

This guide will help you deploy your AlgoTrading application to AWS using Amazon ECS with Fargate.

## Prerequisites

1. **AWS CLI installed and configured**
   ```bash
   aws configure
   ```

2. **Docker installed and running**

3. **AWS Account with appropriate permissions**
   - EC2, ECS, ECR, CloudFormation, IAM, VPC, ALB permissions

## Architecture

- **Frontend**: React app served via Nginx
- **Backend**: FastAPI application
- **Infrastructure**: ECS Fargate with Application Load Balancer
- **Container Registry**: Amazon ECR
- **Database**: SQLite (for development - consider RDS for production)

## Deployment Steps

### Option 1: Windows PowerShell
```powershell
.\deploy.ps1
```

### Option 2: Manual Steps

1. **Deploy Infrastructure**
   ```bash
   aws cloudformation deploy \
     --template-file aws-infrastructure.yml \
     --stack-name algotrading-stack \
     --capabilities CAPABILITY_IAM \
     --region us-east-1
   ```

2. **Get ECR Repository URIs**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name algotrading-stack \
     --query 'Stacks[0].Outputs'
   ```

3. **Login to ECR**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   ```

4. **Build and Push Images**
   ```bash
   # Backend
   cd backend
   docker build -t algotrading-backend .
   docker tag algotrading-backend:latest <backend-ecr-uri>:latest
   docker push <backend-ecr-uri>:latest
   
   # Frontend
   cd ../frontend
   echo "VITE_API_URL=http://<alb-dns>/api" > .env
   docker build -t algotrading-frontend .
   docker tag algotrading-frontend:latest <frontend-ecr-uri>:latest
   docker push <frontend-ecr-uri>:latest
   ```

5. **Update Task Definitions**
   - Replace placeholders in `backend-task-definition.json` and `frontend-task-definition.json`
   - Register task definitions with ECS

6. **Create ECS Services**
   - Create services for both frontend and backend
   - Configure load balancer target groups

## Configuration

### Environment Variables

**Backend**:
- `DATABASE_URL`: SQLite database path (default: `sqlite:///./sql_app.db`)

**Frontend**:
- `VITE_API_URL`: Backend API URL (set during build)

### Security Considerations

1. **CORS Configuration**: Update CORS origins in production
2. **Database**: Consider using Amazon RDS for production
3. **Secrets**: Use AWS Secrets Manager for API keys
4. **SSL/TLS**: Add HTTPS certificate to ALB
5. **Authentication**: Implement proper JWT tokens

## Production Recommendations

1. **Database Migration**
   ```yaml
   # Add to CloudFormation template
   RDSInstance:
     Type: AWS::RDS::DBInstance
     Properties:
       DBInstanceClass: db.t3.micro
       Engine: postgres
       MasterUsername: admin
       MasterUserPassword: !Ref DBPassword
   ```

2. **Secrets Management**
   ```python
   # Update backend to use AWS Secrets Manager
   import boto3
   
   def get_secret(secret_name):
       client = boto3.client('secretsmanager')
       response = client.get_secret_value(SecretId=secret_name)
       return response['SecretString']
   ```

3. **SSL Certificate**
   ```bash
   # Request certificate
   aws acm request-certificate \
     --domain-name yourdomain.com \
     --validation-method DNS
   ```

4. **Auto Scaling**
   ```bash
   # Configure auto scaling
   aws application-autoscaling register-scalable-target \
     --service-namespace ecs \
     --scalable-dimension ecs:service:DesiredCount \
     --resource-id service/algotrading-cluster/algotrading-backend-service \
     --min-capacity 1 \
     --max-capacity 10
   ```

## Monitoring

1. **CloudWatch Logs**: Logs are automatically sent to CloudWatch
2. **CloudWatch Metrics**: Monitor ECS service metrics
3. **ALB Access Logs**: Enable for request tracking

## Troubleshooting

1. **Service not starting**: Check CloudWatch logs
2. **Health check failures**: Verify target group health checks
3. **Database connection issues**: Check security groups and database connectivity

## Cost Optimization

1. **Use Fargate Spot**: For non-critical workloads
2. **Right-size containers**: Adjust CPU/memory based on usage
3. **Schedule scaling**: Scale down during off-hours

## Cleanup

To delete all resources:
```bash
aws cloudformation delete-stack --stack-name algotrading-stack
```

## Support

For issues with deployment, check:
1. CloudFormation events
2. ECS service events
3. CloudWatch logs
4. ALB target group health

## Next Steps

1. Set up CI/CD pipeline with AWS CodePipeline
2. Implement proper monitoring and alerting
3. Add backup strategy for database
4. Implement blue-green deployments