#!/usr/bin/env python3
import json
import boto3
import sys
import time
from pathlib import Path

# Add gateway directory to path to import utils
gateway_dir = Path(__file__).parent.parent.parent / "gateway"
sys.path.append(str(gateway_dir))

from utils import get_or_create_resource_server, get_token

def ensure_user_pool_domain(cognito, user_pool_id):
    """Ensure user pool has a domain for OAuth2 endpoints"""
    try:
        # Check if domain already exists
        response = cognito.describe_user_pool(UserPoolId=user_pool_id)
        user_pool = response.get('UserPool', {})
        domain = user_pool.get('Domain')
        
        if domain:
            print(f"✅ Domain already exists: {domain}")
            return domain
        
        # Create domain if it doesn't exist
        domain_name = user_pool_id.replace("_", "").lower()
        print(f"🔧 Creating domain: {domain_name}")
        
        cognito.create_user_pool_domain(
            Domain=domain_name,
            UserPoolId=user_pool_id
        )
        print(f"✅ Domain created: {domain_name}")
        return domain_name
        
    except Exception as e:
        print(f"❌ Error with domain: {e}")
        return None

def create_new_m2m_client(cognito, user_pool_id, RESOURCE_SERVER_ID):
    """Create a new M2M client with timestamp to avoid conflicts"""
    timestamp = int(time.time())
    client_name = f"MCPServerPoolClient-{timestamp}"
    
    print(f'Creating new m2m client: {client_name}')
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=[f"{RESOURCE_SERVER_ID}/gateway:read", f"{RESOURCE_SERVER_ID}/gateway:write"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    return created["UserPoolClient"]["ClientId"], created["UserPoolClient"]["ClientSecret"]

def refresh_and_update_tokens():
    """Refresh token using existing gateway utils and update all agent configs"""
    
    current_dir = Path(__file__).parent
    
    # Path to master config in gateway/config/
    master_config_path = gateway_dir / "config" / "gateway_runtime_config.json"
    
    if not master_config_path.exists():
        print(f"❌ Master config file not found: {master_config_path}")
        return False
    
    # Read master config
    with open(master_config_path, 'r') as f:
        config = json.load(f)
    
    print("🔍 Setting up Cognito credentials...")
    
    # Initialize Cognito client
    cognito = boto3.client('cognito-idp')
    region = config.get('region', 'us-east-1')
    
    # Use existing user pool ID from previous runs
    user_pool_id = "us-east-1_LgPGIAWFQ"  # From previous output
    RESOURCE_SERVER_ID = 'sample-agentcore-gateway-id'
    
    try:
        print(f"✅ Using existing user pool: {user_pool_id}")
        
        # Ensure domain exists
        domain = ensure_user_pool_domain(cognito, user_pool_id)
        if not domain:
            print("❌ Could not create or find domain")
            return False
        
        # Resource server should already exist from previous run
        print(f"✅ Using existing resource server: {RESOURCE_SERVER_ID}")
        
        # Create new M2M client (doesn't interfere with existing ones)
        client_id, client_secret = create_new_m2m_client(
            cognito, user_pool_id, RESOURCE_SERVER_ID
        )
        print(f"✅ New M2M client: {client_id}")
        
        # Construct scope string
        scope_string = f"{RESOURCE_SERVER_ID}/gateway:read {RESOURCE_SERVER_ID}/gateway:write"
        
        print("🔄 Refreshing token...")
        
        # Get new token
        token_response = get_token(user_pool_id, client_id, client_secret, scope_string, region)
        
        if 'error' in token_response:
            print(f"❌ Token refresh failed: {token_response['error']}")
            return False
        
        if 'access_token' not in token_response:
            print(f"❌ No access token in response: {token_response}")
            return False
        
        # Update master config with new token
        config['access_token'] = token_response['access_token']
        
        # Write updated master config
        with open(master_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Master config updated with new token")
        
        # Create updated agent config template
        agent_config_template = {
            "gateway_url": config.get('gateway_url'),
            "access_token": token_response['access_token'],
            "bearer_token": token_response['access_token'],  # For compatibility
            "gateway_id": config.get('gateway_id'),
            "region": region,
            "user_pool_id": user_pool_id,
            "client_id": client_id,
            "client_secret": client_secret,
            "scope_string": scope_string,
            "services": config.get('services', [])
        }
        
        # Find all agent directories with config subdirectories
        agent_dirs = [d for d in current_dir.iterdir() 
                      if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('__')]
        
        updated_count = 0
        
        for agent_dir in agent_dirs:
            config_dir = agent_dir / "config"
            
            # Create config directory if it doesn't exist
            if not config_dir.exists():
                config_dir.mkdir(exist_ok=True)
                print(f"📁 Created config directory for {agent_dir.name}")
            
            agent_config_file = config_dir / "gateway_runtime_config.json"
            
            # Write updated config to agent directory
            with open(agent_config_file, 'w') as f:
                json.dump(agent_config_template, f, indent=2)
            
            print(f"✅ Updated token for {agent_dir.name}")
            updated_count += 1
        
        print(f"🎉 Updated tokens in {updated_count} agent directories")
        return True
        
    except Exception as e:
        print(f"❌ Error during token refresh: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    refresh_and_update_tokens()
