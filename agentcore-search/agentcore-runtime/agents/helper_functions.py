from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import time
import os
import sys
import boto3
import json

# Add gateway utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'gateway'))
from utils import create_agentcore_role

def configure_runtime(agent_name, agentcore_iam_role, python_file_name):
    boto_session = Session(region_name=os.getenv("AWS_DEFAULT_REGION"))
    region = boto_session.region_name

    agentcore_runtime = Runtime()

    response = agentcore_runtime.configure(
        entrypoint=python_file_name,
        execution_role=agentcore_iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file="requirements.txt",
        region=region,
        agent_name=agent_name
    )
    return response, agentcore_runtime

def check_status(agent_runtime):
    status_response = agent_runtime.status()
    status = status_response.endpoint['status']
    end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    while status not in end_status:
        time.sleep(10)  # INTENTIONAL: Polling interval for AgentCore runtime status
        status_response = agent_runtime.status()
        status = status_response.endpoint['status']
        print(status)
    return status

def launch_agent(agent_name, agent_iam_role, python_file_name):
    """Launch an agent and return runtime info"""
    _, agent_runtime = configure_runtime(agent_name, agent_iam_role, python_file_name)
    launch_result = agent_runtime.launch()
    agent_id = launch_result.agent_id
    agent_arn = launch_result.agent_arn
    
    print(f"{agent_name} ARN: {agent_arn}")
    return {
        'runtime': agent_runtime,
        'id': agent_id,
        'arn': agent_arn,
        'launch_result': launch_result
    }

def save_agent_arn_to_ssm(agent_name, agent_arn):
    """Save agent ARN to SSM Parameter Store"""
    ssm = boto3.client('ssm')
    ssm.put_parameter(
        Name=f'/agents/{agent_name}_arn',
        Value=agent_arn,
        Type='String',
        Overwrite=True
    )
    print(f"Saved {agent_name} ARN to SSM: /agents/{agent_name}_arn")

def test_agent(agent_runtime, test_prompt="Hello, how are you?"):
    """Test an agent runtime"""
    status = check_status(agent_runtime)
    print(f"Agent status: {status}")
    
    if status == 'READY':
        invoke_response = agent_runtime.invoke({"prompt": test_prompt})
        print(f"Test response: {invoke_response}")
        return invoke_response
    else:
        print(f"Agent not ready. Status: {status}")
        return None

def create_agent_role(agent_name, region=None):
    """Create IAM role for a specific agent"""
    # Note: create_agentcore_role doesn't use region parameter
    iam_role = create_agentcore_role(agent_name=agent_name)
    role_arn = iam_role['Role']['Arn']
    role_name = iam_role['Role']['RoleName']
    
    # Add ECR permissions to the role
    add_ecr_permissions_to_role(role_name)
    
    # Add Cognito permissions to the role for token refresh
    add_cognito_permissions_to_role(role_name)
    
    print(f"{agent_name} Role ARN: {role_arn}")
    print(f"{agent_name} Role Name: {role_name}")
    
    return {
        'arn': role_arn,
        'name': role_name,
        'role': iam_role
    }

def add_ecr_permissions_to_role(role_name):
    """Add ECR permissions to an existing IAM role"""
    iam_client = boto3.client('iam')
    
    ecr_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchCheckLayerAvailability"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="ECRAccessPolicy",
            PolicyDocument=json.dumps(ecr_policy)
        )
        print(f"  ✅ Added ECR permissions to role: {role_name}")
    except Exception as e:
        print(f"  ❌ Failed to add ECR permissions to {role_name}: {e}")

def add_cognito_permissions_to_role(role_name):
    """Add Cognito permissions to an existing IAM role for token refresh"""
    iam_client = boto3.client('iam')
    
    cognito_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "cognito-idp:ListUserPools",
                    "cognito-idp:DescribeUserPool",
                    "cognito-idp:ListUserPoolClients",
                    "cognito-idp:DescribeUserPoolClient"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="CognitoTokenRefreshPolicy",
            PolicyDocument=json.dumps(cognito_policy)
        )
        print(f"  ✅ Added Cognito permissions to role: {role_name}")
    except Exception as e:
        print(f"  ❌ Failed to add Cognito permissions to {role_name}: {e}")