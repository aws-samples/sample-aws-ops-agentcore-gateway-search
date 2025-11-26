import boto3
import time
from typing import Dict, List, Any
from base_scenario import BaseScenario, ScenarioResult, ScenarioStatus

class S3SecurityScenario(BaseScenario):
    def __init__(self):
        super().__init__(
            scenario_id="s3_security_001",
            description="S3 bucket without versioning, encryption, lifecycle policy, and access logging"
        )
        self.s3_client = boto3.client('s3')
        self.bucket_name = "agentcore-demo-s3-security"
        
    def setup(self) -> bool:
        """Create S3 bucket with security issues"""
        try:
            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"Bucket {self.bucket_name} already exists, skipping creation")
                return True
            except:
                pass
            
            # Create bucket with minimal configuration
            self.s3_client.create_bucket(Bucket=self.bucket_name)
            
            # Explicitly disable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={'Status': 'Suspended'}
            )
            
            print(f"Created S3 bucket {self.bucket_name} with security issues")
            return True
            
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def execute(self) -> ScenarioResult:
        """Execute scenario - verify bucket exists"""
        start_time = time.time()
        
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            return ScenarioResult(
                scenario_id=self.scenario_id,
                status=ScenarioStatus.COMPLETED,
                issues_found=[],
                fixes_applied=[],
                validation_results={"bucket_created": True},
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
        """Clean up S3 bucket"""
        try:
            # Delete all objects first
            objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if 'Contents' in objects:
                delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': delete_keys}
                )
            
            self.s3_client.delete_bucket(Bucket=self.bucket_name)
            print(f"Cleaned up S3 bucket {self.bucket_name}")
            return True
            
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False
    
    def get_expected_issues(self) -> List[str]:
        """Return expected issues for this scenario"""
        return [
            "versioning_disabled",
            "encryption_disabled", 
            "no_lifecycle_policy",
            "no_access_logging"
        ]
