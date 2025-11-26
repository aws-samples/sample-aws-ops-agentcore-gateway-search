#!/usr/bin/env python3
"""
Deploy all agents to AgentCore Runtime with cleanup capabilities
"""
import os
import sys
import time
import boto3
from pathlib import Path
from helper_functions import create_agent_role, launch_agent, save_agent_arn_to_ssm, test_agent, check_status

def cleanup_agent_resources(agent_name, agent_dir):
    """Clean up existing resources before deployment"""
    print(f"  🧹 Starting comprehensive cleanup for {agent_name}...")
    
    # 1. Remove file artifacts
    print(f"    📁 Cleaning up local file artifacts...")
    artifacts = ['.bedrock_agentcore.yaml', 'Dockerfile', '.dockerignore']
    for artifact in artifacts:
        file_path = Path(agent_dir) / artifact
        if file_path.exists():
            file_path.unlink()
            print(f"      ✅ Removed {artifact}")
        else:
            print(f"      ⚪ {artifact} not found (already clean)")
    
    # 2. AWS resource cleanup
    print(f"    ☁️ Cleaning up AWS resources...")
    try:
        ssm = boto3.client('ssm')
        iam = boto3.client('iam')
        ecr = boto3.client('ecr')
        
        # Remove AgentCore runtime first (to avoid dependency issues)
        print(f"    🤖 Attempting to delete AgentCore runtime...")
        try:
            param_response = ssm.get_parameter(Name=f"/agents/{agent_name}_arn")
            runtime_arn = param_response['Parameter']['Value']
            runtime_id = runtime_arn.split('/')[-1]
            
            print(f"      📋 Found runtime ARN in SSM: {runtime_arn}")
            print(f"      🎯 Extracting runtime ID: {runtime_id}")
            print(f"      🗑️ Deleting AgentCore runtime...")
            
            # Use correct client and method
            agentcore_control_client = boto3.client('bedrock-agentcore-control')
            runtime_delete_response = agentcore_control_client.delete_agent_runtime(
                agentRuntimeId=runtime_id
            )
            print(f"      ✅ Successfully deleted AgentCore runtime: {runtime_id}")
            print(f"      ⏳ Waiting 10 seconds for runtime deletion to propagate...")
            time.sleep(10)  # INTENTIONAL: AWS requires time for runtime deletion to propagate
            
            # Validate runtime deletion
            print(f"      🔍 Validating runtime deletion...")
            try:
                agentcore_control_client.get_agent_runtime(agentRuntimeId=runtime_id)
                print(f"      ⚠️ Warning: Runtime still exists after deletion attempt")
            except agentcore_control_client.exceptions.ResourceNotFoundException:
                print(f"      ✅ Confirmed: Runtime successfully deleted")
            except Exception as validation_error:
                print(f"      ⚠️ Could not validate deletion: {validation_error}")
            
        except ssm.exceptions.ParameterNotFound:
            print(f"      ⚪ No SSM parameter found for {agent_name} - runtime may not exist")
        except Exception as e:
            print(f"      ❌ Runtime cleanup failed: {e}")
            print(f"      💡 This may be expected if the runtime doesn't exist")
        
        # Remove SSM parameter
        print(f"    📋 Cleaning up SSM parameter...")
        try:
            ssm.delete_parameter(Name=f"/agents/{agent_name}_arn")
            print(f"      ✅ Removed SSM parameter: /agents/{agent_name}_arn")
        except ssm.exceptions.ParameterNotFound:
            print(f"      ⚪ SSM parameter not found (already clean)")
        except Exception as e:
            print(f"      ⚠️ SSM parameter cleanup failed: {e}")
        
        # Remove ECR repository
        print(f"    🐳 Cleaning up ECR repository...")
        try:
            ecr.delete_repository(repositoryName=f"bedrock-agentcore-{agent_name}", force=True)
            print(f"      ✅ Removed ECR repository: bedrock-agentcore-{agent_name}")
        except ecr.exceptions.RepositoryNotFoundException:
            print(f"      ⚪ ECR repository not found (already clean)")
        except Exception as e:
            print(f"      ⚠️ ECR repository cleanup failed: {e}")
        
        # Remove IAM role
        print(f"    🔐 Cleaning up IAM role...")
        try:
            role_name = f"agentcore-{agent_name}-role"
            print(f"      🎯 Target role: {role_name}")
            
            # Remove inline policies
            try:
                policies = iam.list_role_policies(RoleName=role_name)
                for policy in policies['PolicyNames']:
                    iam.delete_role_policy(RoleName=role_name, PolicyName=policy)
                    print(f"        ✅ Removed inline policy: {policy}")
            except Exception as e:
                print(f"        ⚪ No inline policies to remove: {e}")
                
            # Remove attached policies
            try:
                attached = iam.list_attached_role_policies(RoleName=role_name)
                for policy in attached['AttachedPolicies']:
                    iam.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
                    print(f"        ✅ Detached policy: {policy['PolicyName']}")
            except Exception as e:
                print(f"        ⚪ No attached policies to remove: {e}")
                
            # Delete role
            iam.delete_role(RoleName=role_name)
            print(f"      ✅ Removed IAM role: {role_name}")
        except iam.exceptions.NoSuchEntityException:
            print(f"      ⚪ IAM role not found (already clean)")
        except Exception as e:
            print(f"      ⚠️ IAM role cleanup failed: {e}")
            
    except Exception as e:
        print(f"    ❌ Some cleanup operations failed: {e}")
    
    print(f"  ✅ Cleanup completed for {agent_name}")
    print(f"  🔍 Validating cleanup before proceeding to deployment...")
    
    # Final validation
    validation_passed = True
    try:
        # Check if runtime still exists
        ssm = boto3.client('ssm')
        try:
            param_response = ssm.get_parameter(Name=f"/agents/{agent_name}_arn")
            print(f"    ⚠️ Warning: SSM parameter still exists after cleanup")
            validation_passed = False
        except ssm.exceptions.ParameterNotFound:
            print(f"    ✅ Confirmed: SSM parameter cleaned up")
    except Exception as e:
        print(f"    ⚠️ Could not validate SSM cleanup: {e}")
    
    if validation_passed:
        print(f"  🎯 Validation passed - ready for deployment")
    else:
        print(f"  ⚠️ Validation warnings detected - proceeding with deployment anyway")
    
    return validation_passed

def deploy_all_agents(cleanup=False, single_agent=None):
    """Deploy all agents with roles, launch, and save ARNs"""
    
    # Agent configurations: (agent_name, python_file_name, directory_name)
    agent_configs = [
        ("intent_classifier_agent", "intent_classifier.py", "intent_classifier"),
        ("troubleshooting_agent", "troubleshooting_agent.py", "troubleshooting_agent"),
        ("execution_agent", "execution_agent.py", "execution_agent"), 
        ("validation_agent", "validation_agent.py", "validation_agent"),
        ("documentation_agent", "documentation_agent.py", "documentation_agent"),
        ("orchestrator_agent", "orchestrator.py", "orchestrator")
    ]
    
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    deployed_agents = {}
    
    print("🚀 Starting AgentCore Runtime deployment for all agents...")
    
    for i, (agent_name, python_file, agent_dir) in enumerate(agent_configs):
        print(f"\n📦 Deploying {agent_name} ({i+1}/{len(agent_configs)})...")
        
        try:
            # Step 1: Create IAM role
            print(f"  1️⃣ Creating IAM role for {agent_name}...")
            role_info = create_agent_role(agent_name, region)
            
            # Wait for IAM role propagation
            print("  ⏳ Waiting for IAM role propagation...")
            time.sleep(10)  # INTENTIONAL: AWS IAM requires time for role propagation
            
            # Step 2: Launch agent
            print(f"  2️⃣ Launching {agent_name}...")
            
            # Change to agent directory
            original_dir = os.getcwd()
            os.chdir(agent_dir)
            
            try:
                launch_info = launch_agent(agent_name, role_info['role'], python_file)
                
                # Step 3: Wait for agent to be ready (check_status handles the polling loop)
                print(f"  3️⃣ Waiting for {agent_name} to be ready (this may take several minutes)...")
                status = check_status(launch_info['runtime'])  # This function polls until ready
                
                if status == 'READY':
                    # Step 4: Save ARN to SSM only after agent is ready
                    print(f"  4️⃣ Saving {agent_name} ARN to SSM...")
                    save_agent_arn_to_ssm(agent_name, launch_info['arn'])
                    
                    # Step 5: Test agent
                    print(f"  5️⃣ Testing {agent_name}...")
                    test_prompt = f"Hello from {agent_name}"
                    # test_agent also calls check_status internally, but agent should already be ready
                    invoke_response = launch_info['runtime'].invoke({"prompt": test_prompt})
                    print(f"  Test response: {invoke_response}")
                    
                    deployed_agents[agent_name] = {
                        'role': role_info,
                        'launch': launch_info,
                        'status': status,
                        'test_result': invoke_response
                    }
                    
                    print(f"  ✅ {agent_name} deployed successfully!")
                else:
                    print(f"  ❌ {agent_name} failed to reach READY status: {status}")
                
            finally:
                os.chdir(original_dir)
                
        except Exception as e:
            print(f"  ❌ Failed to deploy {agent_name}: {str(e)}")
            
        # Wait between agent deployments to avoid overwhelming the system
        if i < len(agent_configs) - 1:  # Don't wait after the last agent
            print("  ⏳ Waiting before next agent deployment...")
            time.sleep(30)
    
    print(f"\n🎉 Deployment complete! Deployed {len(deployed_agents)} agents:")
    for agent_name, info in deployed_agents.items():
        print(f"  - {agent_name}: {info['launch']['arn']} (Status: {info['status']})")
    
    return deployed_agents

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy AgentCore Runtime agents')
    parser.add_argument('--cleanup', action='store_true', help='Clean up existing resources before deployment')
    parser.add_argument('--agent', type=str, help='Deploy single agent by name')
    
    args = parser.parse_args()
    
    # Agent configurations: (agent_name, python_file_name, directory_name)
    agent_configs = [
        ("intent_classifier_agent", "intent_classifier.py", "intent_classifier"),
        ("troubleshooting_agent", "troubleshooting_agent.py", "troubleshooting_agent"),
        ("execution_agent", "execution_agent.py", "execution_agent"), 
        ("validation_agent", "validation_agent.py", "validation_agent"),
        ("documentation_agent", "documentation_agent.py", "documentation_agent"),
        ("orchestrator_agent", "orchestrator.py", "orchestrator")
    ]
    
    # Filter for single agent if specified
    if args.agent:
        agent_configs = [config for config in agent_configs if config[0] == args.agent]
        if not agent_configs:
            print(f"❌ Agent '{args.agent}' not found")
            sys.exit(1)
    
    # Add cleanup to the deployment process
    if args.cleanup:
        print("🧹 Cleanup mode enabled - will remove existing resources before deployment")
        for agent_name, _, agent_dir in agent_configs:
            cleanup_agent_resources(agent_name, agent_dir)
    
    deployed = deploy_all_agents()
    print(f"\nDeployment summary: {len(deployed)} agents deployed successfully")
