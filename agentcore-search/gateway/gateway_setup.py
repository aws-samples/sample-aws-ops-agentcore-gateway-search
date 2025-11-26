#!/usr/bin/env python3
"""
Admin Gateway Setup - Run once to create gateway and save configuration
"""
import os
import sys
import json

# Add gateway path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
        
        print(f"\n🎉 Setup complete! Users can now run the UI.")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = setup_gateway()
    exit(0 if success else 1)
