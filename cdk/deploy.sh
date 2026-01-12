#!/bin/bash
# Deployment script for Asterisk PBX CDK stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Asterisk PBX CDK Deployment ===${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

if ! command -v cdk &> /dev/null; then
    echo -e "${RED}CDK CLI is not installed. Installing...${NC}"
    npm install -g aws-cdk
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed.${NC}"
    exit 1
fi

# Get AWS account and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${GREEN}AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}AWS Region: ${AWS_REGION}${NC}"

# Setup Python virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv .venv
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Bootstrap CDK (if needed)
echo -e "${YELLOW}Bootstrapping CDK (if needed)...${NC}"
cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION} || echo "CDK already bootstrapped"

# Build and push Docker images
echo -e "${YELLOW}Building and pushing Docker images...${NC}"

# Login to ECR
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build Python app image
echo -e "${YELLOW}Building Python app image...${NC}"
cd ..
docker build -f cdk/Dockerfile -t python-brain-pbx .
docker tag python-brain-pbx:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/python-brain-pbx:latest

# Push Python app image
echo -e "${YELLOW}Pushing Python app image to ECR...${NC}"
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/python-brain-pbx:latest

cd cdk

# Synthesize CloudFormation template
echo -e "${YELLOW}Synthesizing CloudFormation template...${NC}"
cdk synth

# Deploy stack
echo -e "${YELLOW}Deploying stack...${NC}"
read -p "Do you want to deploy the stack? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cdk deploy --require-approval never
    echo -e "${GREEN}Deployment complete!${NC}"
else
    echo -e "${YELLOW}Deployment cancelled.${NC}"
fi

deactivate

