# GitHub Actions Setup Guide

Quick setup guide for GitHub Actions CI/CD workflows.

## Quick Start

### 1. Add GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |

### 2. Create IAM User in AWS

1. Go to AWS Console → IAM → Users → Create user
2. Name: `github-actions-deployer`
3. Attach policy: `PowerUserAccess` (or create custom policy)
4. Create access key
5. Copy the access key ID and secret access key to GitHub secrets

### 3. Bootstrap CDK (First Time)

Run this locally or let the workflow do it automatically:

```bash
cd cdk
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
```

### 4. Test the Workflow

1. Push to `main` branch or create a PR
2. Go to **Actions** tab in GitHub
3. Watch the workflow run

## Workflow Overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `deploy.yml` | Push to main/master | Full deployment (build + deploy) |
| `build-images.yml` | Push/PR | Build Docker images |
| `test.yml` | Push/PR | Run tests and linting |
| `destroy.yml` | Manual only | Destroy stack (⚠️ dangerous) |

## Manual Deployment

1. Go to **Actions** → **Deploy to AWS ECS**
2. Click **Run workflow**
3. Select:
   - Branch: `main`
   - Environment: `dev` (or staging/production)
   - Skip image build: `false` (unless you already built)
4. Click **Run workflow**

## Troubleshooting

### "AWS credentials not found"
- Check secrets are named exactly: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Verify secrets are added to the correct repository

### "ECR login failed"
- Verify IAM user has `ecr:GetAuthorizationToken` permission
- Check AWS region matches your ECR repositories

### "CDK bootstrap failed"
- Run bootstrap manually: `cdk bootstrap aws://ACCOUNT_ID/REGION`
- Check IAM permissions include CloudFormation access

### "Stack deployment failed"
- Check CloudFormation console for detailed errors
- Review workflow logs for CDK errors
- Verify all required AWS services are available in your region

## Security Best Practices

1. ✅ Use least-privilege IAM policies
2. ✅ Rotate AWS credentials regularly
3. ✅ Enable branch protection on main/master
4. ✅ Require PR reviews before merging
5. ✅ Use environment protection for production
6. ✅ Monitor AWS CloudTrail for access logs

## Next Steps

- [ ] Add GitHub secrets
- [ ] Create IAM user with appropriate permissions
- [ ] Bootstrap CDK in AWS
- [ ] Test workflow with a small change
- [ ] Set up branch protection rules
- [ ] Configure environment protection for production

