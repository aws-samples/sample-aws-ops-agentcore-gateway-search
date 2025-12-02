#!/usr/bin/env python3
"""
Comprehensive Workshop Resource Cleanup Script
Cleans up all resources created during the AgentCore workshop including:
- AgentCore Runtime agents and supporting resources
- Gateway infrastructure and authentication
- Demo scenario resources
- CodeBuild projects and roles
"""

import boto3
import json
import argparse
import time
from typing import List, Dict, Optional
from pathlib import Path

class WorkshopCleanup:
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.clients = {
            'agentcore_control': boto3.client('bedrock-agentcore-control', region_name=region),
            'agentcore_runtime': boto3.client('bedrock-agentcore', region_name=region),
            'iam': boto3.client('iam', region_name=region),
            'ssm': boto3.client('ssm', region_name=region),
            'ecr': boto3.client('ecr', region_name=region),
            'logs': boto3.client('logs', region_name=region),
            'cognito': boto3.client('cognito-idp', region_name=region),
            's3': boto3.client('s3', region_name=region),
            'lambda': boto3.client('lambda', region_name=region),
            'codebuild': boto3.client('codebuild', region_name=region),
            'cloudwatch': boto3.client('cloudwatch', region_name=region)
        }
        
        # Resource naming patterns
        self.agent_names = [
            'intent_classifier_agent', 'troubleshooting_agent', 'execution_agent',
            'validation_agent', 'documentation_agent', 'orchestrator_agent'
        ]
        self.scenario_resources = {
            'lambda': ['agentcore-demo-lambda-perf'],
            's3': ['agentcore-demo-s3-security'],
            'cloudwatch': []  # Log groups and alarms
        }

    def cleanup_agentcore_runtimes(self) -> bool:
        """Clean up all AgentCore Runtime agents and supporting resources"""
        print("🤖 Cleaning up AgentCore Runtime resources...")
        success = True
        
        for agent_name in self.agent_names:
            print(f"  🔧 Processing {agent_name}...")
            
            try:
                # 1. Get runtime ARN from SSM
                runtime_arn = self._get_agent_arn_from_ssm(agent_name)
                
                if runtime_arn:
                    # 2. Delete AgentCore runtime
                    runtime_id = runtime_arn.split('/')[-1]
                    print(f"    🗑️ Deleting runtime: {runtime_id}")
                    self.clients['agentcore_control'].delete_agent_runtime(
                        agentRuntimeId=runtime_id
                    )
                    print(f"    ✅ Runtime deleted")
                    time.sleep(5)  # INTENTIONAL: Wait for AgentCore runtime deletion to propagate
                
                # 3. Clean up SSM parameter
                self._delete_ssm_parameter(f"/agents/{agent_name}_arn")
                
                # 4. Clean up ECR repository
                self._delete_ecr_repository(f"bedrock-agentcore-{agent_name}")
                
                # 5. Clean up IAM role
                self._delete_iam_role(f"agentcore-{agent_name}-role")
                
                # 6. Clean up CloudWatch log groups
                self._delete_log_groups_by_pattern(f"/aws/bedrock-agentcore/runtimes/{agent_name}")
                
                print(f"    ✅ {agent_name} cleanup completed")
                
            except Exception as e:
                print(f"    ❌ Error cleaning {agent_name}: {str(e)}")
                success = False
        
        return success

    def cleanup_gateway_resources(self) -> bool:
        """Clean up AgentCore Gateway and authentication resources"""
        print("🌐 Cleaning up Gateway resources...")
        success = True
        
        try:
            # 1. Find and delete gateway from config file
            gateway_id = self._get_gateway_id_from_config()
            if gateway_id:
                print(f"  🗑️ Deleting gateway: {gateway_id}")
                try:
                    # First, delete all gateway targets
                    self._delete_gateway_targets(gateway_id)
                    
                    # Wait for target deletions to propagate
                    print(f"  ⏳ Waiting for target deletions to propagate...")
                    time.sleep(10)
                    
                    # Then delete the gateway
                    self.clients['agentcore_control'].delete_gateway(gatewayIdentifier=gateway_id)
                    print(f"  ✅ Gateway deleted successfully")
                    time.sleep(5)  # Wait for gateway deletion to propagate
                except Exception as e:
                    print(f"  ⚠️ Gateway deletion error: {str(e)}")
                    print(f"  💡 You may need to delete the gateway manually via console")
            else:
                print(f"  ⚪ No gateway configuration found")
            
            # 2. Clean up Cognito resources
            self._cleanup_cognito_resources()
            
            # 3. Clean up S3 bucket for schemas
            self._delete_s3_bucket_by_pattern("agentcore-gateway-search")
            
            # 4. Clean up gateway IAM roles
            self._delete_iam_roles_by_pattern("agentcore-gateway")
            
        except Exception as e:
            print(f"  ❌ Error cleaning gateway resources: {str(e)}")
            success = False
        
        return success

    def cleanup_scenario_resources(self, service: Optional[str] = None) -> bool:
        """Clean up demo scenario resources"""
        print("🎯 Cleaning up scenario resources...")
        success = True
        
        services_to_clean = [service] if service else self.scenario_resources.keys()
        
        for svc in services_to_clean:
            if svc == 'lambda':
                success &= self._cleanup_lambda_scenarios()
            elif svc == 's3':
                success &= self._cleanup_s3_scenarios()
            elif svc == 'cloudwatch':
                success &= self._cleanup_cloudwatch_scenarios()
        
        return success

    def cleanup_codebuild_resources(self) -> bool:
        """Clean up CodeBuild projects and roles"""
        print("🏗️ Cleaning up CodeBuild resources...")
        success = True
        
        try:
            # 1. Delete CodeBuild projects
            for agent_name in self.agent_names:
                project_name = f"bedrock-agentcore-{agent_name}-builder"
                self._delete_codebuild_project(project_name)
            
            # 2. Clean up CodeBuild service roles
            self._delete_iam_roles_by_pattern("AmazonBedrockAgentCoreSDKCodeBuild")
            
        except Exception as e:
            print(f"  ❌ Error cleaning CodeBuild resources: {str(e)}")
            success = False
        
        return success

    # Helper methods
    def _get_agent_arn_from_ssm(self, agent_name: str) -> Optional[str]:
        """Get agent ARN from SSM Parameter Store"""
        try:
            response = self.clients['ssm'].get_parameter(Name=f"/agents/{agent_name}_arn")
            return response['Parameter']['Value']
        except:
            return None

    def _delete_ssm_parameter(self, parameter_name: str):
        """Delete SSM parameter"""
        try:
            self.clients['ssm'].delete_parameter(Name=parameter_name)
            print(f"    ✅ Deleted SSM parameter: {parameter_name}")
        except Exception as e:
            print(f"    ⚪ SSM parameter not found: {parameter_name}")

    def _delete_ecr_repository(self, repo_name: str):
        """Delete ECR repository"""
        try:
            self.clients['ecr'].delete_repository(
                repositoryName=repo_name,
                force=True
            )
            print(f"    ✅ Deleted ECR repository: {repo_name}")
        except Exception as e:
            print(f"    ⚪ ECR repository not found: {repo_name}")

    def _delete_iam_role(self, role_name: str):
        """Delete IAM role and all attached policies"""
        try:
            # List and detach managed policies
            policies = self.clients['iam'].list_attached_role_policies(RoleName=role_name)
            for policy in policies['AttachedPolicies']:
                self.clients['iam'].detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
            
            # Delete inline policies
            inline_policies = self.clients['iam'].list_role_policies(RoleName=role_name)
            for policy_name in inline_policies['PolicyNames']:
                self.clients['iam'].delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
            
            # Delete role
            self.clients['iam'].delete_role(RoleName=role_name)
            print(f"    ✅ Deleted IAM role: {role_name}")
        except Exception as e:
            print(f"    ⚪ IAM role not found: {role_name}")

    def _delete_iam_roles_by_pattern(self, pattern: str):
        """Delete IAM roles matching pattern"""
        try:
            roles = self.clients['iam'].list_roles()
            for role in roles['Roles']:
                if pattern in role['RoleName']:
                    self._delete_iam_role(role['RoleName'])
        except Exception as e:
            print(f"    ❌ Error deleting roles with pattern {pattern}: {str(e)}")

    def _delete_log_groups_by_pattern(self, pattern: str):
        """Delete CloudWatch log groups matching pattern"""
        try:
            log_groups = self.clients['logs'].describe_log_groups(
                logGroupNamePrefix=pattern
            )
            for group in log_groups['logGroups']:
                self.clients['logs'].delete_log_group(
                    logGroupName=group['logGroupName']
                )
                print(f"    ✅ Deleted log group: {group['logGroupName']}")
        except Exception as e:
            print(f"    ⚪ No log groups found with pattern: {pattern}")

    def _cleanup_lambda_scenarios(self) -> bool:
        """Clean up Lambda scenario resources"""
        print("  🔧 Cleaning Lambda scenarios...")
        success = True
        
        for func_name in self.scenario_resources['lambda']:
            try:
                # Delete function
                self.clients['lambda'].delete_function(FunctionName=func_name)
                print(f"    ✅ Deleted Lambda function: {func_name}")
                
                # Delete associated IAM role
                role_name = f"{func_name}-role"
                self._delete_iam_role(role_name)
                
            except Exception as e:
                print(f"    ⚪ Lambda function not found: {func_name}")
        
        return success

    def _cleanup_s3_scenarios(self) -> bool:
        """Clean up S3 scenario resources"""
        print("  🔧 Cleaning S3 scenarios...")
        success = True
        
        for bucket_name in self.scenario_resources['s3']:
            try:
                # Empty bucket first
                self._empty_s3_bucket(bucket_name)
                
                # Delete bucket
                self.clients['s3'].delete_bucket(Bucket=bucket_name)
                print(f"    ✅ Deleted S3 bucket: {bucket_name}")
                
            except Exception as e:
                print(f"    ⚪ S3 bucket not found: {bucket_name}")
        
        return success

    def _cleanup_cloudwatch_scenarios(self) -> bool:
        """Clean up CloudWatch scenario resources"""
        print("  🔧 Cleaning CloudWatch scenarios...")
        success = True
        
        try:
            # Delete alarms with agentcore-demo prefix
            alarms = self.clients['cloudwatch'].describe_alarms(
                AlarmNamePrefix='agentcore-demo'
            )
            for alarm in alarms['MetricAlarms']:
                self.clients['cloudwatch'].delete_alarms(
                    AlarmNames=[alarm['AlarmName']]
                )
                print(f"    ✅ Deleted alarm: {alarm['AlarmName']}")
                
        except Exception as e:
            print(f"    ⚪ No CloudWatch alarms found")
        
        return success

    def _empty_s3_bucket(self, bucket_name: str):
        """Empty S3 bucket before deletion"""
        try:
            objects = self.clients['s3'].list_objects_v2(Bucket=bucket_name)
            if 'Contents' in objects:
                delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
                self.clients['s3'].delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': delete_keys}
                )
        except:
            pass

    def _delete_s3_bucket_by_pattern(self, pattern: str):
        """Delete S3 buckets matching pattern"""
        try:
            buckets = self.clients['s3'].list_buckets()
            for bucket in buckets['Buckets']:
                if pattern in bucket['Name']:
                    self._empty_s3_bucket(bucket['Name'])
                    self.clients['s3'].delete_bucket(Bucket=bucket['Name'])
                    print(f"    ✅ Deleted S3 bucket: {bucket['Name']}")
        except Exception as e:
            print(f"    ⚪ No S3 buckets found with pattern: {pattern}")

    def _cleanup_cognito_resources(self):
        """Clean up Cognito user pools and clients"""
        try:
            user_pools = self.clients['cognito'].list_user_pools(MaxResults=50)
            for pool in user_pools['UserPools']:
                if 'agentcore' in pool['Name'].lower():
                    # Delete user pool clients first
                    clients = self.clients['cognito'].list_user_pool_clients(
                        UserPoolId=pool['Id']
                    )
                    for client in clients['UserPoolClients']:
                        self.clients['cognito'].delete_user_pool_client(
                            UserPoolId=pool['Id'],
                            ClientId=client['ClientId']
                        )
                    
                    # Delete user pool
                    self.clients['cognito'].delete_user_pool(UserPoolId=pool['Id'])
                    print(f"    ✅ Deleted Cognito user pool: {pool['Name']}")
        except Exception as e:
            print(f"    ⚪ No Cognito resources found")

    def _get_gateway_id_from_config(self) -> Optional[str]:
        """Get gateway ID from config file"""
        try:
            config_path = Path('agentcore-search/gateway/config/gateway_runtime_config.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('gateway_id')
        except Exception as e:
            print(f"    ⚪ Could not read gateway config: {str(e)}")
        return None

    def _delete_gateway_targets(self, gateway_id: str):
        """Delete all targets associated with a gateway"""
        try:
            # List all targets for the gateway
            response = self.clients['agentcore_control'].list_gateway_targets(
                gatewayIdentifier=gateway_id
            )
            
            targets = response.get('items', [])
            if targets:
                print(f"    🎯 Found {len(targets)} gateway targets to delete")
                for target in targets:
                    target_id = target.get('targetId')
                    target_name = target.get('name', target_id)
                    if target_id:
                        try:
                            self.clients['agentcore_control'].delete_gateway_target(
                                gatewayIdentifier=gateway_id,
                                targetId=target_id
                            )
                            print(f"    ✅ Deleted gateway target: {target_name} ({target_id})")
                            time.sleep(2)  # Wait between deletions
                        except Exception as e:
                            print(f"    ⚠️ Error deleting target {target_name}: {str(e)}")
            else:
                print(f"    ⚪ No gateway targets found")
        except Exception as e:
            print(f"    ⚠️ Error listing gateway targets: {str(e)}")

    def _delete_codebuild_project(self, project_name: str):
        """Delete CodeBuild project"""
        try:
            self.clients['codebuild'].delete_project(name=project_name)
            print(f"    ✅ Deleted CodeBuild project: {project_name}")
        except Exception as e:
            print(f"    ⚪ CodeBuild project not found: {project_name}")

def main():
    parser = argparse.ArgumentParser(description='Cleanup AgentCore Workshop Resources')
    parser.add_argument('--service', choices=['agentcore', 'gateway', 'scenarios', 'codebuild', 'all'],
                       default='all', help='Service to clean up')
    parser.add_argument('--scenario-type', choices=['lambda', 's3', 'cloudwatch'],
                       help='Specific scenario type to clean (when service=scenarios)')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    
    args = parser.parse_args()
    
    print(f"🧹 AgentCore Workshop Cleanup - Region: {args.region}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No resources will be deleted")
    
    cleanup = WorkshopCleanup(region=args.region)
    
    if args.dry_run:
        print("📋 Resources that would be cleaned:")
        print("  - AgentCore Runtime agents and supporting resources")
        print("  - Gateway infrastructure and authentication")
        print("  - Demo scenario resources")
        print("  - CodeBuild projects and roles")
        return
    
    success = True
    
    if args.service in ['agentcore', 'all']:
        success &= cleanup.cleanup_agentcore_runtimes()
    
    if args.service in ['gateway', 'all']:
        success &= cleanup.cleanup_gateway_resources()
    
    if args.service in ['scenarios', 'all']:
        success &= cleanup.cleanup_scenario_resources(args.scenario_type)
    
    if args.service in ['codebuild', 'all']:
        success &= cleanup.cleanup_codebuild_resources()
    
    if success:
        print("\n🎉 Cleanup completed successfully!")
    else:
        print("\n⚠️ Cleanup completed with some errors. Check output above.")

if __name__ == "__main__":
    main()
