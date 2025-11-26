#!/usr/bin/env python3
"""
Fix Action Framework - Tracks automated fixes applied by agents
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
import uuid

@dataclass
class FixAction:
    """Represents a single fix action performed by an agent"""
    action_id: str
    action_type: str  # "create", "update", "delete", "configure", "restart", "scale"
    resource_type: str  # "lambda", "s3", "iam", "cloudwatch", "ec2", etc.
    resource_identifier: str  # ARN, name, or ID of the resource
    description: str  # Human-readable description of what was fixed
    commands_executed: List[str]  # List of commands/API calls made
    before_state: Dict  # Resource state before fix
    after_state: Dict  # Resource state after fix
    timestamp: str  # ISO timestamp when fix was applied
    success: bool  # Whether the fix was successful
    error_message: Optional[str] = None  # Error details if fix failed
    validation_status: str = "pending"  # "pending", "validated", "failed", "rollback_needed"
    
    @classmethod
    def create_new(cls, action_type: str, resource_type: str, resource_identifier: str, 
                   description: str, commands_executed: List[str], before_state: Dict, 
                   after_state: Dict, success: bool, error_message: Optional[str] = None):
        """Create a new FixAction with auto-generated ID and timestamp"""
        return cls(
            action_id=str(uuid.uuid4())[:8],
            action_type=action_type,
            resource_type=resource_type,
            resource_identifier=resource_identifier,
            description=description,
            commands_executed=commands_executed,
            before_state=before_state,
            after_state=after_state,
            timestamp=datetime.now().isoformat(),
            success=success,
            error_message=error_message
        )
    
    def to_dict(self) -> Dict:
        """Convert FixAction to dictionary for JSON serialization"""
        return asdict(self)
    
    def get_summary(self) -> str:
        """Get a brief summary of the fix action"""
        status = "✅" if self.success else "❌"
        return f"{status} {self.action_type.title()} {self.resource_type}: {self.description}"

@dataclass
class FixResult:
    """Container for multiple fix actions and overall results"""
    fixes_applied: List[FixAction]
    total_fixes: int
    successful_fixes: int
    failed_fixes: int
    requires_validation: bool
    validation_suggestions: List[str]
    
    @classmethod
    def from_fixes(cls, fixes: List[FixAction], validation_suggestions: List[str] = None):
        """Create FixResult from a list of FixActions"""
        successful = sum(1 for fix in fixes if fix.success)
        failed = len(fixes) - successful
        
        return cls(
            fixes_applied=fixes,
            total_fixes=len(fixes),
            successful_fixes=successful,
            failed_fixes=failed,
            requires_validation=len(fixes) > 0,
            validation_suggestions=validation_suggestions or []
        )
    
    def get_summary(self) -> str:
        """Get overall summary of fix results"""
        if self.total_fixes == 0:
            return "No fixes applied"
        
        return f"{self.successful_fixes}/{self.total_fixes} fixes successful"
