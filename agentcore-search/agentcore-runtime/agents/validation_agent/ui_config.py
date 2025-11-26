#!/usr/bin/env python3
"""
UI Configuration Reader - Reads gateway config from config/ folder (no setup)
"""
import os
import json
import boto3
from boto3.session import Session
import utils

def get_gateway_config_for_ui():
    """Read gateway configuration from config file - no setup, just read"""
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'gateway_runtime_config.json')
    
    try:
        if not os.path.exists(config_file):
            print("❌ Gateway not configured. Please run gateway_setup.py first.")
            return None, None
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return config['gateway_url'], config['access_token']
        
    except Exception as e:
        print(f"❌ Error reading gateway config: {e}")
        print("Please run gateway_setup.py to configure the gateway.")
        return None, None

def refresh_access_token():
    """Refresh the access token using stored Cognito credentials"""
    try:
        boto_session = Session()
        region = boto_session.region_name or os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Cognito configuration (same as in gateway_config.py)
        USER_POOL_NAME = "sample-agentcore-gateway-pool"
        RESOURCE_SERVER_ID = "sample-agentcore-gateway-id"
        CLIENT_NAME = "sample-agentcore-gateway-client"
        scope_string = f"{RESOURCE_SERVER_ID}/gateway:read {RESOURCE_SERVER_ID}/gateway:write"
        
        # Get existing Cognito resources
        cognito = boto3.client("cognito-idp", region_name=region)
        user_pool_id = utils.get_or_create_user_pool(cognito, USER_POOL_NAME)
        client_id, client_secret = utils.get_or_create_m2m_client(cognito, user_pool_id, CLIENT_NAME, RESOURCE_SERVER_ID)
        
        # Get new token
        token_response = utils.get_token(user_pool_id, client_id, client_secret, scope_string, region)
        
        if "access_token" in token_response:
            # Update config file with new token
            config_file = os.path.join(os.path.dirname(__file__), 'config', 'gateway_runtime_config.json')
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            config['access_token'] = token_response["access_token"]
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return token_response["access_token"]
        else:
            print(f"Token refresh failed: {token_response}")
            return None
            
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None

def get_full_config_for_ui():
    """Read full gateway configuration from config file"""
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'gateway_runtime_config.json')
    
    try:
        if not os.path.exists(config_file):
            return None
        
        with open(config_file, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"❌ Error reading gateway config: {e}")
        return None
