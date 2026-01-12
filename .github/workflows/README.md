# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD of the Asterisk PBX CDK deployment.

## Workflows

### 1. `deploy.yml` - Main Deployment Workflow

**Triggers:**
- Push to `main` or `master` branch
- Manual workflow dispatch

**What it does:**
1. Builds and pushes Docker images to ECR
2. Deploys CDK stack to AWS
3. Outputs stack information

**Manual inputs:**
- `environment`: Choose deployment environment (dev/staging/production)
- `skip_image_build`: Skip Docker image build step

### 2. `build-images.yml` - Docker Image Build

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests
- Manual workflow dispatch

**What it does:**
1. Builds Docker images locally (for PRs)
2. Builds and pushes to ECR (for main/master branches)

### 3. `test.yml` - Testing and Validation

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests
- Manual workflow dispatch

**What it does:**
1. Lints CDK code (flake8, black, mypy)
2. Tests Python application
3. Validates CDK stack (cdk synth)
4. Tests Docker build

### 4. `destroy.yml` - Stack Destruction

**Triggers:**
- Manual workflow dispatch only

**What it does:**
1. Destroys CDK stack (requires confirmation)

**⚠️ WARNING:** This will delete all AWS resources including databases!

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

### Required Secrets

- `AWS_ACCESS_KEY_ID` - AWS access key ID with deployment permissions
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key

### Recommended IAM Policy

The AWS credentials should have permissions for:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:*",
        "ec2:*",
        "rds:*",
        "cloudformation:*",
        "iam:*",
        "logs:*",
        "elasticloadbalancing:*",
        "servicediscovery:*",
        "secretsmanager:*",
        "s3:*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Or use the AWS managed policy: `PowerUserAccess` (for development) or create a custom policy with least privilege.

## Environment Setup

### 1. Configure GitHub Secrets

1. Go to your repository → Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

### 2. Configure Environments (Optional)

For environment-specific deployments:

1. Go to Settings → Environments
2. Create environments: `dev`, `staging`, `production`
3. Add environment-specific secrets if needed
4. Configure protection rules (required reviewers, etc.)

### 3. AWS Account Setup

Before first deployment:

1. Ensure AWS CLI is configured locally
2. Bootstrap CDK (can be done manually or via workflow):
   ```bash
   cd cdk
   cdk bootstrap aws://ACCOUNT_ID/REGION
   ```

## Usage

### Automatic Deployment

Push to `main` or `master` branch:
```bash
git push origin main
```

The workflow will automatically:
1. Build Docker images
2. Push to ECR
3. Deploy CDK stack

### Manual Deployment

1. Go to Actions tab in GitHub
2. Select "Deploy to AWS ECS" workflow
3. Click "Run workflow"
4. Select environment and options
5. Click "Run workflow"

### Testing Changes

Create a pull request to trigger:
- Code linting
- CDK validation
- Docker build tests

### Destroying Stack

⚠️ **Use with caution!**

1. Go to Actions tab
2. Select "Destroy CDK Stack" workflow
3. Click "Run workflow"
4. Enter stack name (default: `AsteriskPbxStack`)
5. Type `destroy` in confirmation field
6. Click "Run workflow"

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![Deploy](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Deploy%20to%20AWS%20ECS/badge.svg)
![Test](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Test%20and%20Lint/badge.svg)
```

## Troubleshooting

### Workflow Fails on ECR Login

- Verify AWS credentials are correct
- Check IAM permissions include `ecr:GetAuthorizationToken`
- Ensure region matches your ECR repositories

### CDK Bootstrap Fails

- Run bootstrap manually: `cdk bootstrap aws://ACCOUNT_ID/REGION`
- Check AWS credentials have CloudFormation permissions

### Docker Build Fails

- Check Dockerfile path is correct
- Verify all dependencies are in requirements.txt
- Check build context includes necessary files

### Deployment Fails

- Check CloudFormation events in AWS Console
- Review CDK diff output in workflow logs
- Verify all required resources are available in AWS

## Customization

### Change AWS Region

Update `AWS_REGION` in workflow files:
```yaml
env:
  AWS_REGION: us-west-2  # Change to your preferred region
```

### Add More Environments

1. Create environment in GitHub Settings → Environments
2. Update workflow to reference new environment
3. Add environment-specific configuration

### Modify Build Steps

Edit the workflow YAML files to add:
- Additional tests
- Security scans
- Notifications (Slack, email, etc.)
- Custom deployment steps

## Best Practices

1. **Use branch protection**: Require PR reviews before merging to main
2. **Environment protection**: Require approval for production deployments
3. **Secrets rotation**: Rotate AWS credentials regularly
4. **Monitor costs**: Set up AWS billing alerts
5. **Review changes**: Always review CDK diff before deploying
6. **Test first**: Run tests on PRs before merging
7. **Backup data**: Ensure RDS backups are configured before production

