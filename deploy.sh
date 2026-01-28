#!/bin/bash

# AWS Deployment Script for AlgoTrading Application
# Make sure AWS CLI is configured with appropriate credentials

set -e

# Configuration
STACK_NAME="algotrading-stack"
REGION="us-east-1"  # Change to your preferred region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Deploying AlgoTrading Application to AWS..."
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"

# Step 1: Deploy Infrastructure
echo "Step 1: Deploying infrastructure..."
aws cloudformation deploy \
  --template-file aws-infrastructure.yml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --region $REGION

# Get stack outputs
echo "Getting stack outputs..."
VPC_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`VPC`].OutputValue' --output text)
SUBNETS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnets`].OutputValue' --output text)
CLUSTER_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' --output text)
BACKEND_ECR=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`BackendECRRepository`].OutputValue' --output text)
FRONTEND_ECR=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`FrontendECRRepository`].OutputValue' --output text)
ALB_DNS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)

echo "Infrastructure deployed successfully!"
echo "Load Balancer DNS: $ALB_DNS"

# Step 2: Create CloudWatch Log Groups
echo "Step 2: Creating CloudWatch log groups..."
aws logs create-log-group --log-group-name /ecs/algotrading-backend --region $REGION || true
aws logs create-log-group --log-group-name /ecs/algotrading-frontend --region $REGION || true

# Step 3: Login to ECR
echo "Step 3: Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Step 4: Build and push backend image
echo "Step 4: Building and pushing backend image..."
cd backend
docker build -t algotrading-backend .
docker tag algotrading-backend:latest $BACKEND_ECR:latest
docker push $BACKEND_ECR:latest
cd ..

# Step 5: Build and push frontend image
echo "Step 5: Building and pushing frontend image..."
cd frontend
# Create .env file for build
echo "VITE_API_URL=http://$ALB_DNS/api" > .env
docker build -t algotrading-frontend .
docker tag algotrading-frontend:latest $FRONTEND_ECR:latest
docker push $FRONTEND_ECR:latest
cd ..

# Step 6: Update task definitions with actual values
echo "Step 6: Updating task definitions..."
EXECUTION_ROLE_ARN=$(aws iam list-roles --query "Roles[?contains(RoleName, 'ECSTaskExecutionRole')].Arn" --output text)

# Update backend task definition
sed -i "s/ACCOUNT_ID/$ACCOUNT_ID/g" backend-task-definition.json
sed -i "s/REGION/$REGION/g" backend-task-definition.json
sed -i "s|arn:aws:iam::ACCOUNT_ID:role/STACK_NAME-ECSTaskExecutionRole-XXXXX|$EXECUTION_ROLE_ARN|g" backend-task-definition.json

# Update frontend task definition
sed -i "s/ACCOUNT_ID/$ACCOUNT_ID/g" frontend-task-definition.json
sed -i "s/REGION/$REGION/g" frontend-task-definition.json
sed -i "s|arn:aws:iam::ACCOUNT_ID:role/STACK_NAME-ECSTaskExecutionRole-XXXXX|$EXECUTION_ROLE_ARN|g" frontend-task-definition.json

# Step 7: Register task definitions
echo "Step 7: Registering task definitions..."
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json --region $REGION
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json --region $REGION

# Step 8: Create ECS services
echo "Step 8: Creating ECS services..."
SECURITY_GROUP=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=AlgoTrading-ECS-SG" --query 'SecurityGroups[0].GroupId' --output text --region $REGION)
SUBNET1=$(echo $SUBNETS | cut -d',' -f1)
SUBNET2=$(echo $SUBNETS | cut -d',' -f2)

# Backend service
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name algotrading-backend-service \
  --task-definition algotrading-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=$(aws elbv2 describe-target-groups --names AlgoTrading-Backend-TG --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION),containerName=backend,containerPort=8000 \
  --region $REGION

# Frontend service
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name algotrading-frontend-service \
  --task-definition algotrading-frontend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=$(aws elbv2 describe-target-groups --names AlgoTrading-Frontend-TG --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION),containerName=frontend,containerPort=80 \
  --region $REGION

echo "Deployment completed successfully!"
echo "Your application will be available at: http://$ALB_DNS"
echo "Backend API docs: http://$ALB_DNS/docs"
echo ""
echo "Note: It may take a few minutes for the services to become healthy."