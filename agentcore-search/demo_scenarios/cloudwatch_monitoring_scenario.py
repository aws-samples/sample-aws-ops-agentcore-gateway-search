import boto3
import time
from typing import Dict, List, Any
from base_scenario import BaseScenario, ScenarioResult, ScenarioStatus

class CloudWatchMonitoringScenario(BaseScenario):
    def __init__(self):
        super().__init__(
            scenario_id="cloudwatch_monitoring_001",
            description="Lambda function without CloudWatch alarms, log retention, and custom metrics"
        )
        self.cloudwatch_client = boto3.client('cloudwatch')
        self.logs_client = boto3.client('logs')
        self.lambda_function_name = "agentcore-demo-lambda-perf"  # Use existing Lambda
        self.log_group_name = f"/aws/lambda/{self.lambda_function_name}"
        
    def setup(self) -> bool:
        """Setup monitoring gaps scenario"""
        try:
            # Ensure log group exists but with no retention policy
            try:
                self.logs_client.create_log_group(logGroupName=self.log_group_name)
                print(f"Created log group: {self.log_group_name}")
            except self.logs_client.exceptions.ResourceAlreadyExistsException:
                print(f"Log group {self.log_group_name} already exists")
            
            # Remove any existing retention policy (set to never expire)
            try:
                self.logs_client.delete_retention_policy(logGroupName=self.log_group_name)
                print("Removed log retention policy (logs will be kept forever)")
            except:
                pass  # No retention policy to remove
            
            return True
            
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def execute(self) -> ScenarioResult:
        """Execute scenario - verify monitoring gaps exist"""
        start_time = time.time()
        
        try:
            # Check if alarms exist for the Lambda function
            alarms = self.cloudwatch_client.describe_alarms(
                AlarmNamePrefix=f"{self.lambda_function_name}-"
            )
            
            # Check log retention
            log_groups = self.logs_client.describe_log_groups(
                logGroupNamePrefix=self.log_group_name
            )
            
            return ScenarioResult(
                scenario_id=self.scenario_id,
                status=ScenarioStatus.COMPLETED,
                issues_found=[],
                fixes_applied=[],
                validation_results={
                    "alarms_count": len(alarms['MetricAlarms']),
                    "log_group_exists": len(log_groups['logGroups']) > 0
                },
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
        """Clean up monitoring resources"""
        try:
            # Delete any alarms created for this function
            alarms = self.cloudwatch_client.describe_alarms(
                AlarmNamePrefix=f"{self.lambda_function_name}-"
            )
            
            if alarms['MetricAlarms']:
                alarm_names = [alarm['AlarmName'] for alarm in alarms['MetricAlarms']]
                self.cloudwatch_client.delete_alarms(AlarmNames=alarm_names)
                print(f"Deleted {len(alarm_names)} CloudWatch alarms")
            
            return True
            
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False
    
    def get_expected_issues(self) -> List[str]:
        """Return expected issues for this scenario"""
        return [
            "no_error_alarms",
            "no_duration_alarms",
            "no_log_retention_policy",
            "no_custom_metrics"
        ]
