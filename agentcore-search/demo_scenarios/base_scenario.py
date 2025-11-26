from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum

class ScenarioStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ScenarioResult:
    scenario_id: str
    status: ScenarioStatus
    issues_found: List[Dict[str, Any]]
    fixes_applied: List[Dict[str, Any]]
    validation_results: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None

class BaseScenario(ABC):
    def __init__(self, scenario_id: str, description: str):
        self.scenario_id = scenario_id
        self.description = description
        self.status = ScenarioStatus.PENDING
        
    @abstractmethod
    def setup(self) -> bool:
        """Setup the scenario environment"""
        pass
    
    @abstractmethod
    def execute(self) -> ScenarioResult:
        """Execute the scenario and return results"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """Clean up scenario resources"""
        pass
    
    @abstractmethod
    def get_expected_issues(self) -> List[str]:
        """Return list of expected issues this scenario should detect"""
        pass
