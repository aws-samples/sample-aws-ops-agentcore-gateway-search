# Workshop Cleanup

Clean up all workshop resources:

```bash
# Clean everything
python3 cleanup_workshop_resources.py

# Clean specific services
python3 cleanup_workshop_resources.py --service agentcore
python3 cleanup_workshop_resources.py --service gateway  
python3 cleanup_workshop_resources.py --service scenarios

# See what would be deleted
python3 cleanup_workshop_resources.py --dry-run
```

Cleans up: AgentCore runtimes, ECR repos, IAM roles, SSM parameters, gateway, Cognito, S3 buckets, Lambda functions, CloudWatch resources, CodeBuild projects.
