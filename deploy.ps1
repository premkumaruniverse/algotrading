# AWS Deployment Script for AlgoTrading Application (PowerShell)
# Make sure AWS CLI is configured with appropriate credentials

$ErrorActionPreference = "Stop"

# Configuration
$STACK_NAME = "algotrading-stack"
$REGION = "us-east-1"  # Change to your preferred region
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

Write-Host "Deploying AlgoTrading Application to AWS..."
Write-Host "Account ID: $ACCOUNT_ID"
Write-Host "Region: $REGION"
Write-Host "Stack Name: $STACK_NAME"

# Step 1: Deploy Infrastructure
Write-Host "Step 1: Deploying infrastructure..."
aws cloudformation deploy --template-file aws-infrastructure.yml --stack-name $STACK_NAME --capabilities CAPABILITY_IAM --region $REGION

# Get stack outputs
Write-Host "Getting stack outputs..."
$VPC_ID = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`VPC`].OutputValue' --output text
$SUBNETS = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnets`].OutputValue' --output text
$CLUSTER_NAME = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' --output text
$BACKEND_ECR = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`BackendECRRepository`].OutputValue' --output text
$FRONTEND_ECR = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`FrontendECRRepository`].OutputValue' --output text
$ALB_DNS = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text

Write-Host "Infrastructure deployed successfully!"
Write-Host "Load Balancer DNS: $ALB_DNS"

# Step 2: Create CloudWatch Log Groups
Write-Host "Step 2: Creating CloudWatch log groups..."
try { aws logs create-log-group --log-group-name /ecs/algotrading-backend --region $REGION } catch {}
try { aws logs create-log-group --log-group-name /ecs/algotrading-frontend --region $REGION } catch {}

# Step 3: Login to ECR
Write-Host "Step 3: Logging into ECR..."
$ECR_TOKEN = aws ecr get-login-password --region $REGION
$ECR_TOKEN | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Step 4: Build and push backend image
Write-Host "Step 4: Building and pushing backend image..."
Set-Location backend
docker build -t algotrading-backend .
docker tag algotrading-backend:latest "$BACKEND_ECR:latest"
docker push "$BACKEND_ECR:latest"
Set-Location ..

# Step 5: Build and push frontend image
Write-Host "Step 5: Building and pushing frontend image..."
Set-Location frontend
# Create .env file for build
"VITE_API_URL=http://$ALB_DNS/api" | Out-File -FilePath .env -Encoding utf8
docker build -t algotrading-frontend .
docker tag algotrading-frontend:latest "$FRONTEND_ECR:latest"
docker push "$FRONTEND_ECR:latest"
Set-Location ..

# Step 6: Update task definitions with actual values
Write-Host "Step 6: Updating task definitions..."
$EXECUTION_ROLE_ARN = aws iam list-roles --query "Roles[?contains(RoleName, 'ECSTaskExecutionRole')].Arn" --output text

# Update backend task definition
$backendTaskDef = Get-Content backend-task-definition.json -Raw
$backendTaskDef = $backendTaskDef -replace "ACCOUNT_ID", $ACCOUNT_ID
$backendTaskDef = $backendTaskDef -replace "REGION", $REGION
$backendTaskDef = $backendTaskDef -replace "arn:aws:iam::ACCOUNT_ID:role/STACK_NAME-ECSTaskExecutionRole-XXXXX", $EXECUTION_ROLE_ARN
$backendTaskDef | Out-File -FilePath backend-task-definition.json -Encoding utf8

# Update frontend task definition
$frontendTaskDef = Get-Content frontend-task-definition.json -Raw
$frontendTaskDef = $frontendTaskDef -replace "ACCOUNT_ID", $ACCOUNT_ID
$frontendTaskDef = $frontendTaskDef -replace "REGION", $REGION
$frontendTaskDef = $frontendTaskDef -replace "arn:aws:iam::ACCOUNT_ID:role/STACK_NAME-ECSTaskExecutionRole-XXXXX", $EXECUTION_ROLE_ARN
$frontendTaskDef | Out-File -FilePath frontend-task-definition.json -Encoding utf8

# Step 7: Register task definitions
Write-Host "Step 7: Registering task definitions..."
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json --region $REGION
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json --region $REGION

# Step 8: Create ECS services
Write-Host "Step 8: Creating ECS services..."
$SECURITY_GROUP = aws ec2 describe-security-groups --filters "Name=group-name,Values=AlgoTrading-ECS-SG" --query 'SecurityGroups[0].GroupId' --output text --region $REGION
$SUBNET_ARRAY = $SUBNETS -split ','
$SUBNET1 = $SUBNET_ARRAY[0]
$SUBNET2 = $SUBNET_ARRAY[1]

# Backend service
$BACKEND_TG_ARN = aws elbv2 describe-target-groups --names AlgoTrading-Backend-TG --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION
aws ecs create-service --cluster $CLUSTER_NAME --service-name algotrading-backend-service --task-definition algotrading-backend --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=$BACKEND_TG_ARN,containerName=backend,containerPort=8000" --region $REGION

# Frontend service
$FRONTEND_TG_ARN = aws elbv2 describe-target-groups --names AlgoTrading-Frontend-TG --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION
aws ecs create-service --cluster $CLUSTER_NAME --service-name algotrading-frontend-service --task-definition algotrading-frontend --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=$FRONTEND_TG_ARN,containerName=frontend,containerPort=80" --region $REGION

Write-Host "Deployment completed successfully!"
Write-Host "Your application will be available at: http://$ALB_DNS"
Write-Host "Backend API docs: http://$ALB_DNS/docs"
Write-Host ""
Write-Host "Note: It may take a few minutes for the services to become healthy."