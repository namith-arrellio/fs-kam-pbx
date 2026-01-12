# CDK Deployment for Asterisk PBX

This directory contains AWS CDK code to deploy the Asterisk PBX (FreeSWITCH/Kamailio) stack to AWS ECS.

## Architecture

The stack deploys:
- **FreeSWITCH**: VoIP PBX server
- **Kamailio**: SIP proxy server
- **MySQL**: RDS database for Kamailio
- **Python Flask App**: Control and monitoring application
- **Network Load Balancer**: For SIP traffic (UDP/TCP port 5060)
- **Application Load Balancer**: For Python Flask app (port 5001)

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Node.js** (for CDK CLI)
3. **Python 3.9+**
4. **Docker** (for building and pushing images)

## Setup Instructions

### 1. Install CDK CLI

```bash
npm install -g aws-cdk
```

### 2. Install Python Dependencies

```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

This creates the necessary S3 bucket and IAM roles for CDK deployments.

### 4. Build and Push Docker Images

#### Build Python App Image

```bash
# From the project root directory
docker build -f cdk/Dockerfile -t python-brain-pbx .

# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1  # Change to your preferred region

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag and push Python app image
docker tag python-brain-pbx:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python-brain-pbx:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python-brain-pbx:latest
```

#### Build FreeSWITCH Image (Optional)

If you want to customize FreeSWITCH with your configs:

```bash
# Create a Dockerfile for FreeSWITCH
docker build -t freeswitch-pbx -f Dockerfile.freeswitch .

# Tag and push
docker tag freeswitch-pbx:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/freeswitch-pbx:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/freeswitch-pbx:latest
```

#### Build Kamailio Image (Optional)

If you want to customize Kamailio with your configs:

```bash
# Create a Dockerfile for Kamailio
docker build -t kamailio-pbx -f Dockerfile.kamailio .

# Tag and push
docker tag kamailio-pbx:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kamailio-pbx:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kamailio-pbx:latest
```

### 5. Configure CDK Context (Optional)

You can set account and region in `cdk.json` or via context:

```bash
cdk deploy --context account=123456789012 --context region=us-east-1
```

### 6. Synthesize CloudFormation Template

```bash
cdk synth
```

This generates the CloudFormation template without deploying.

### 7. Deploy the Stack

```bash
cdk deploy
```

This will:
- Create VPC with public and private subnets
- Create RDS MySQL instance
- Create ECS cluster
- Create ECR repositories
- Deploy ECS services for FreeSWITCH, Kamailio, and Python app
- Create load balancers
- Set up service discovery

### 8. View Outputs

After deployment, CDK will output:
- SIP endpoint URL
- Python app endpoint URL
- MySQL endpoint
- ECR repository URIs
- MySQL secret ARN

## Configuration

### Updating Python App for ECS

The Python app needs to use environment variables to connect to services in ECS. An example ECS-compatible version is provided in `python-brain/app.ecs.py.example`. Update `python-brain/app.py` to use environment variables:

```python
import os
fs_host = os.getenv("FS_HOST", "freeswitch.pbx.local")
fs_port = int(os.getenv("FS_PORT", "8021"))
fs_password = os.getenv("FS_PASSWORD", "ClueCon")
fs_conn = InboundESL(host=fs_host, port=fs_port, password=fs_password)
```

The CDK stack already sets these environment variables, so the app will automatically connect via service discovery.

### Environment Variables

You can modify environment variables in `asterisk_pbx_stack.py`:
- FreeSWITCH ESL password
- MySQL connection settings
- Service discovery names

### Resource Sizing

Adjust CPU and memory in the task definitions:
- FreeSWITCH: Currently 1024 CPU / 2048 MB RAM
- Kamailio: Currently 256 CPU / 512 MB RAM
- Python App: Currently 256 CPU / 512 MB RAM

## Production Considerations

Before deploying to production:

1. **Enable Multi-AZ for RDS**: Set `multi_az=True` in RDS configuration
2. **Change Removal Policy**: Set `removal_policy=RemovalPolicy.RETAIN` for RDS
3. **Enable Deletion Protection**: Set `deletion_protection=True` for RDS
4. **Increase Resource Sizes**: Adjust CPU/memory based on load
5. **Enable Auto Scaling**: Add auto-scaling policies for ECS services
6. **Use Secrets Manager**: Store all passwords in AWS Secrets Manager
7. **Enable CloudWatch Alarms**: Set up monitoring and alerting
8. **Configure WAF**: Add AWS WAF for the Application Load Balancer
9. **Use Private Subnets**: Consider moving more services to private subnets
10. **Enable VPC Flow Logs**: For network monitoring

## Mounting Configuration Files

To mount FreeSWITCH or Kamailio configuration files, you'll need to:

1. Store configs in S3 or EFS
2. Mount them as volumes in the task definition
3. Or bake them into custom Docker images

Example for EFS:

```python
# Create EFS file system
fs = efs.FileSystem(self, "ConfigFS", vpc=vpc)

# Add volume to task definition
freeswitch_task.add_volume(
    name="config",
    efs_volume_configuration=ecs.EfsVolumeConfiguration(
        file_system_id=fs.file_system_id,
    ),
)
```

## Important Notes

### Network Load Balancer Integration

If you encounter an error about `attach_to_network_target_group` not existing, you may need to manually configure the target group registration. This can happen with different CDK versions. Alternative approaches:

1. **Use CDK v2.100.0 or later** (recommended)
2. **Manually register targets** after deployment using AWS CLI:
   ```bash
   # Get target group ARNs from CloudFormation outputs
   # Register ECS service tasks manually if needed
   ```

### Python App Update Required

Before deploying, ensure `python-brain/app.py` uses environment variables for database and FreeSWITCH connections. See `python-brain/app.ecs.py.example` for reference.

## Troubleshooting

### Check ECS Service Logs

```bash
# Get log group name from CloudWatch
aws logs tail /ecs/freeswitch --follow
aws logs tail /ecs/kamailio --follow
aws logs tail /ecs/python-app --follow
```

### Check Service Status

```bash
aws ecs list-services --cluster PBXCluster
aws ecs describe-services --cluster PBXCluster --services <service-name>
```

### Test SIP Connection

```bash
# Get SIP endpoint from CDK outputs
sip_endpoint=$(aws cloudformation describe-stacks --stack-name AsteriskPbxStack --query 'Stacks[0].Outputs[?OutputKey==`SIPEndpoint`].OutputValue' --output text)
echo $sip_endpoint
```

## Cleanup

To destroy all resources:

```bash
cdk destroy
```

**Warning**: This will delete all resources including the RDS database and all data.

## Cost Estimation

Approximate monthly costs (us-east-1):
- RDS MySQL t3.micro: ~$15
- ECS Fargate (3 services): ~$30-50
- NAT Gateway: ~$32
- Load Balancers: ~$20
- Data Transfer: Variable

Total: ~$100-150/month (excluding data transfer)

## Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [FreeSWITCH Documentation](https://freeswitch.org/confluence/)
- [Kamailio Documentation](https://www.kamailio.org/w/documentation/)

