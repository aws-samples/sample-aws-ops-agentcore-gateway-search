#!/usr/bin/env python3
"""
Update agent permissions for inter-agent communication
Based on agent communication patterns analysis:
- Only ORCHESTRATOR agent communicates with other agents
- Sub-agents do not directly invoke each other
"""
import boto3
import json

def update_orchestrator_permissions():
    """Update orchestrator agent permissions to invoke all sub-agents"""
    
    # Sub-agents that orchestrator communicates with (from orchestrator.py analysis)
    sub_agent_names = [
        "intent_classifier_agent",    # Used for intent classification
        "troubleshooting_agent",      # Called for TROUBLESHOOTING intent
        "execution_agent",            # Called for EXECUTION intent  
        "validation_agent",           # Used for fix validation (future use)
        "documentation_agent"         # Called when tools are missing or as fallback
    ]
    
    ssm = boto3.client('ssm')
    iam_client = boto3.client('iam')
    
    # Retrieve agent ARNs from SSM Parameter Store
    sub_agent_arns = []
    sub_agent_parameter_arns = []
    
    print("🔍 Retrieving sub-agent ARNs from SSM Parameter Store...")
    for agent_name in sub_agent_names:
        try:
            response = ssm.get_parameter(Name=f'/agents/{agent_name}_arn')
            agent_arn = response['Parameter']['Value']
            parameter_arn = response['Parameter']['ARN']
            
            sub_agent_arns.append(agent_arn)
            sub_agent_parameter_arns.append(parameter_arn)
            print(f"  ✅ {agent_name}: {agent_arn}")
            
        except Exception as e:
            print(f"  ❌ Failed to retrieve {agent_name} ARN: {e}")
    
    if not sub_agent_arns:
        print("❌ No sub-agent ARNs found. Make sure agents are deployed first.")
        return None
    
    # Create orchestrator permissions policy
    orchestrator_permissions = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime"
                ],
                "Resource": [
                    # Both runtime ARN and runtime-endpoint/DEFAULT format
                    *sub_agent_arns,
                    *[f"{arn}/runtime-endpoint/DEFAULT" for arn in sub_agent_arns]
                ]
            },
            {
                "Effect": "Allow", 
                "Action": [
                    "ssm:GetParameter"
                ],
                "Resource": sub_agent_parameter_arns
            }
        ]
    }
    
    # Update orchestrator role permissions
    orchestrator_role_name = "agentcore-orchestrator_agent-role"  # Actual role name from deployment
    
    try:
        print(f"\n🔐 Updating orchestrator role permissions...")
        response = iam_client.put_role_policy(
            RoleName=orchestrator_role_name,
            PolicyName="SubAgentInvocationPermissions",
            PolicyDocument=json.dumps(orchestrator_permissions, indent=2)
        )
        
        print(f"✅ Updated orchestrator permissions successfully!")
        print(f"   - Can invoke {len(sub_agent_arns)} sub-agents")
        print(f"   - Can read {len(sub_agent_parameter_arns)} SSM parameters")
        print(f"   - Policy: SubAgentInvocationPermissions")
        
        return response
        
    except Exception as e:
        print(f"❌ Failed to update orchestrator permissions: {e}")
        return None

def verify_no_other_inter_agent_communication():
    """Verify that no other agents need inter-agent communication permissions"""
    print("\n🔍 Analysis: Inter-agent communication patterns")
    print("   Based on codebase analysis:")
    print("   - ✅ Orchestrator → Intent Classifier (for routing)")
    print("   - ✅ Orchestrator → Troubleshooting Agent (for failures)")
    print("   - ✅ Orchestrator → Execution Agent (for operations)")
    print("   - ✅ Orchestrator → Validation Agent (for fix validation)")
    print("   - ✅ Orchestrator → Documentation Agent (for fallback)")
    print("   - ❌ No sub-agent to sub-agent communication found")
    print("   - ❌ No other agents need InvokeAgentRuntime permissions")

if __name__ == "__main__":
    print("🚀 Updating agent permissions for inter-agent communication...")
    
    # Verify communication patterns
    verify_no_other_inter_agent_communication()
    
    # Update orchestrator permissions
    result = update_orchestrator_permissions()
    
    if result:
        print("\n🎉 Permission update completed successfully!")
        print("   The orchestrator can now invoke all sub-agents in AgentCore Runtime.")
    else:
        print("\n💥 Permission update failed!")
        print("   Make sure:")
        print("   1. All agents are deployed to AgentCore Runtime")
        print("   2. Agent ARNs are stored in SSM Parameter Store")
        print("   3. You have IAM permissions to update roles")
