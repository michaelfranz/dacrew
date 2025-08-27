#!/bin/bash

# Deployment script for dacrew
set -e

# Default values
ENVIRONMENT=${ENVIRONMENT:-"dev"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
DOCKER_IMAGE_NAME="dacrew"
ECR_REPOSITORY=${ECR_REPOSITORY:-"dacrew"}
CLUSTER_NAME=${CLUSTER_NAME:-"dacrew-cluster"}
SERVICE_NAME=${SERVICE_NAME:-"dacrew-service"}

echo "🚀 Deploying dacrew to $ENVIRONMENT environment..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install it first."
    exit 1
fi

# Build Docker image
echo "🐳 Building Docker image..."
docker build -t $DOCKER_IMAGE_NAME .

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Tag and push image
echo "📤 Pushing image to ECR..."
docker tag $DOCKER_IMAGE_NAME:latest $ECR_URI/$ECR_REPOSITORY:latest
docker push $ECR_URI/$ECR_REPOSITORY:latest

# Create ECS cluster if it doesn't exist
echo "🏗️ Creating ECS cluster..."
aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION 2>/dev/null || \
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION

# Create task definition
echo "📋 Creating task definition..."
cat > task-definition.json << EOF
{
    "family": "dacrew",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "dacrew",
            "image": "$ECR_URI/$ECR_REPOSITORY:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "ENVIRONMENT",
                    "value": "$ENVIRONMENT"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/dacrew",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
EOF

# Register task definition
echo "📝 Registering task definition..."
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION

# Create log group if it doesn't exist
echo "📊 Creating CloudWatch log group..."
aws logs describe-log-groups --log-group-name-prefix "/ecs/dacrew" --region $AWS_REGION 2>/dev/null || \
aws logs create-log-group --log-group-name "/ecs/dacrew" --region $AWS_REGION

# Create or update service
echo "🔧 Creating/updating ECS service..."
aws ecs describe-services --services $SERVICE_NAME --cluster $CLUSTER_NAME --region $AWS_REGION 2>/dev/null
if [ $? -eq 0 ]; then
    # Update existing service
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition dacrew \
        --region $AWS_REGION
else
    # Create new service
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition dacrew \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678],securityGroups=[sg-12345678],assignPublicIp=ENABLED}" \
        --region $AWS_REGION
fi

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: http://your-load-balancer-url"
echo "📊 Monitor logs: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups/log-group/\$252Fecs\$252Fdacrew"
