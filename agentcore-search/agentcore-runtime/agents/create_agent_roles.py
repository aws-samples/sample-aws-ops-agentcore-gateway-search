#!/usr/bin/env python3
"""
Create IAM roles for AgentCore Runtime agents
"""
import os
import sys

# Add gateway utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'gateway'))
from utils import create_agentcore_role

def create_agent_role(agent_name, region=None):
    """Create IAM role for a specific agent"""
    if not region:
        region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    iam_role = create_agentcore_role(agent_name=agent_name, region=region)
    role_arn = iam_role['Role']['Arn']
    role_name = iam_role['Role']['RoleName']
    
    print(f"{agent_name} Role ARN: {role_arn}")
    print(f"{agent_name} Role Name: {role_name}")
    
    return {
        'arn': role_arn,
        'name': role_name,
        'role': iam_role
    }

if __name__ == "__main__":
    # Agent names to create roles for
    agent_names = [
        "intent_classifier_agent",
        "troubleshooting_agent",
        "execution_agent", 
        "validation_agent",
        "documentation_agent",
        "orchestrator_agent"
    ]
    
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    roles = {}
    
    # Create roles for each agent
    for agent_name in agent_names:
        roles[agent_name] = create_agent_role(agent_name, region)
    
    print("\nAll agent roles created successfully!")
    for agent_name, role_info in roles.items():
        print(f"{agent_name}: {role_info['arn']}")
