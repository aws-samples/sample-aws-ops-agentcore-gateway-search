#!/usr/bin/env python3

import sys
import argparse
from typing import Dict, Type
from base_scenario import BaseScenario

# Import all scenario classes
from lambda_performance_scenario import LambdaPerformanceScenario
from s3_security_scenario import S3SecurityScenario
from cloudwatch_monitoring_scenario import CloudWatchMonitoringScenario

# Registry of available scenarios
SCENARIOS: Dict[str, Type[BaseScenario]] = {
    'lambda': LambdaPerformanceScenario,
    's3': S3SecurityScenario,
    'cloudwatch': CloudWatchMonitoringScenario,
}

def list_scenarios():
    """List all available scenarios"""
    print("Available scenarios:")
    for service, scenario_class in SCENARIOS.items():
        scenario = scenario_class()
        print(f"  {service}: {scenario.description}")

def run_scenario(service: str):
    """Run scenario for specified service"""
    if service not in SCENARIOS:
        print(f"❌ Unknown service: {service}")
        print(f"Available services: {', '.join(SCENARIOS.keys())}")
        return False
    
    scenario_class = SCENARIOS[service]
    scenario = scenario_class()
    
    print(f"🚀 Running {service} scenario: {scenario.description}")
    
    if scenario.setup():
        result = scenario.execute()
        if result.status.value == "completed":
            print(f"✅ Scenario created successfully!")
            expected_issues = scenario.get_expected_issues()
            print(f"🔧 Expected issues: {', '.join(expected_issues)}")
            return True
        else:
            print(f"❌ Failed to create scenario: {result.error_message}")
            return False
    else:
        print("❌ Scenario setup failed")
        return False

def main():
    parser = argparse.ArgumentParser(description='AgentCore Demo Scenario Runner')
    parser.add_argument('service', nargs='?', help='Service to run scenario for (lambda, s3, cloudwatch)')
    parser.add_argument('--list', action='store_true', help='List available scenarios')
    
    args = parser.parse_args()
    
    if args.list:
        list_scenarios()
        return
    
    if not args.service:
        print("❌ Please specify a service or use --list to see available scenarios")
        parser.print_help()
        return
    
    run_scenario(args.service)

if __name__ == "__main__":
    main()
