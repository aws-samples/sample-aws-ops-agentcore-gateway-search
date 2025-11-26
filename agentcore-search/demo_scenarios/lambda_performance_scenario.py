import boto3
import time
import json
from typing import Dict, List, Any
from base_scenario import BaseScenario, ScenarioResult, ScenarioStatus

class LambdaPerformanceScenario(BaseScenario):
    def __init__(self):
        super().__init__(
            scenario_id="lambda_performance_001",
            description="Lambda function with insufficient memory, short timeout, and missing CloudWatch permissions"
        )
        self.lambda_client = boto3.client('lambda')
        self.iam_client = boto3.client('iam')
        self.function_name = "agentcore-demo-lambda-perf"
        self.role_name = "agentcore-demo-lambda-role"
        
    def setup(self) -> bool:
        """Create Lambda function with performance issues"""
        try:
            # Create IAM role without CloudWatch permissions
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }
            
            try:
                self.iam_client.create_role(
                    RoleName=self.role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy)
                )
                print(f"Created IAM role: {self.role_name}")
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                print(f"IAM role {self.role_name} already exists, using existing role")
            
            account_id = boto3.client('sts').get_caller_identity()['Account']
            role_arn = f"arn:aws:iam::{account_id}:role/{self.role_name}"
            
            # Wait for role to be available
            time.sleep(10)  # INTENTIONAL: AWS IAM role needs time to become available
            
            # Create simple Lambda code
            lambda_code = '''
def handler(event, context):
    import time
    # Simulate some processing that might need more memory/time
    data = [i for i in range(10000)]
    time.sleep(1)
    return {"statusCode": 200, "body": "Hello from Lambda!"}
'''
            
            # Create zip file in memory
            import zipfile
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                zip_file.writestr('lambda_function.py', lambda_code)
            zip_buffer.seek(0)
            
            # Create Lambda with problematic config
            self.lambda_client.create_function(
                FunctionName=self.function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.handler',
                Code={'ZipFile': zip_buffer.read()},
                MemorySize=128,  # Too low
                Timeout=3        # Too short
            )
            
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def execute(self) -> ScenarioResult:
        """Execute scenario - just verify resources are created"""
        start_time = time.time()
        
        try:
            # Just verify the function exists with problematic config
            response = self.lambda_client.get_function(FunctionName=self.function_name)
            
            return ScenarioResult(
                scenario_id=self.scenario_id,
                status=ScenarioStatus.COMPLETED,
                issues_found=[],  # Troubleshooting agent will detect these
                fixes_applied=[],
                validation_results={"function_created": True, "function_arn": response['Configuration']['FunctionArn']},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ScenarioResult(
                scenario_id=self.scenario_id,
                status=ScenarioStatus.FAILED,
                issues_found=[],
                fixes_applied=[],
                validation_results={},
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def cleanup(self) -> bool:
        """Clean up created resources"""
        try:
            self.lambda_client.delete_function(FunctionName=self.function_name)
            self.iam_client.delete_role(RoleName=self.role_name)
            return True
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False
    
    def get_expected_issues(self) -> List[str]:
        """Return expected issues for this scenario"""
        return [
            "insufficient_memory",
            "short_timeout", 
            "missing_cloudwatch_permissions"
        ]
