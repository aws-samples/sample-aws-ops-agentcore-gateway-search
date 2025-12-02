#!/usr/bin/env python3
"""
Admin Gateway Setup - Run once to create gateway and save configuration
"""
import os
import sys
import json
import shutil

# Add gateway path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def copy_config_to_agents(config_file):
    """Copy gateway config to all agent config directories"""
    print("\n📋 Copying gateway configuration to agent directories...")
    
    # Get the agentcore-runtime/agents directory
    gateway_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(gateway_dir)
    agents_dir = os.path.join(project_root, 'agentcore-runtime', 'agents')
    
    # Validate agents directory exists
    if not os.path.exists(agents_dir):
        print(f"⚠️  Warning: Agents directory not found at {agents_dir}")
        return False
    
    # List of agent directories
    agent_names = [
        'intent_classifier',
        'troubleshooting_agent',
        'execution_agent',
        'validation_agent',
        'documentation_agent',
        'orchestrator'
    ]
    
    copied_count = 0
    for agent_name in agent_names:
        agent_dir = os.path.join(agents_dir, agent_name)
        
        # Validate agent directory exists
        if not os.path.exists(agent_dir):
            print(f"  ⚠️  Agent directory not found: {agent_name}")
            continue
        
        # Create config directory if it doesn't exist
        agent_config_dir = os.path.join(agent_dir, 'config')
        if not os.path.exists(agent_config_dir):
            os.makedirs(agent_config_dir)
            print(f"  📁 Created config directory for {agent_name}")
        
        # Copy the config file
        dest_config_file = os.path.join(agent_config_dir, 'gateway_runtime_config.json')
        try:
            shutil.copy2(config_file, dest_config_file)
            print(f"  ✅ Copied config to {agent_name}")
            copied_count += 1
        except Exception as e:
            print(f"  ❌ Failed to copy config to {agent_name}: {e}")
    
    print(f"\n✅ Gateway configuration copied to {copied_count}/{len(agent_names)} agents")
    return copied_count > 0

def setup_gateway():
    """Admin setup - creates gateway and saves config to file"""
    # Set AWS region
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        from gateway_config import setup_gateway
        
        print("🚀 Admin Gateway Setup - Creating gateway infrastructure...")
        config = setup_gateway(['s3', 'lambda', 'eks', 'cloudwatch'])
        
        # Save configuration to config folder
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        
        # Create config directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            print(f"📁 Created config directory: {config_dir}")
        
        config_file = os.path.join(config_dir, 'gateway_runtime_config.json')
        
        gateway_config = {
            'gateway_url': config['gateway_url'],
            'access_token': config['access_token'],
            'gateway_id': config['gateway_id'],
            'region': config['region'],
            'services': ['s3', 'lambda', 'eks', 'cloudwatch']
        }
        
        with open(config_file, 'w') as f:
            json.dump(gateway_config, f, indent=2)
        
        print(f"\n✅ Gateway Setup Complete!")
        print(f"Gateway URL: {config['gateway_url']}")
        print(f"Gateway ID: {config['gateway_id']}")
        print(f"Region: {config['region']}")
        print(f"Services: S3, Lambda, EKS, CloudWatch")
        print(f"Config saved to: {config_file}")
        
        # Copy config to all agent directories
        copy_config_to_agents(config_file)
        
        print(f"\n🎉 Setup complete! Users can now run the UI.")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = setup_gateway()
    exit(0 if success else 1)
