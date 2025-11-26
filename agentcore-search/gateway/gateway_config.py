import os
import boto3
import json
from boto3.session import Session
import utils

# Cache for gateway configuration
_gateway_cache = {}

def setup_gateway_once(services=['s3', 'lambda', 'eks', 'cloudwatch']):
    """One-time gateway setup - call this once at startup"""
    cache_key = tuple(sorted(services))
    
    if cache_key in _gateway_cache:
        print("Gateway already set up, using cached configuration")
        return _gateway_cache[cache_key]
    
    print("Setting up gateway (one-time setup)...")
    config = setup_gateway(services)
    
    # Cache the result
    _gateway_cache[cache_key] = {
        'gateway_url': config['gateway_url'],
        'access_token': config['access_token'],
        'gateway_id': config['gateway_id'],
        'region': config['region']
    }
    
    print("✅ Gateway setup complete and cached")
    return _gateway_cache[cache_key]

def get_gateway_url_for_ui(services=['s3', 'lambda', 'eks', 'cloudwatch']):
    """Get gateway URL and token for UI - uses cached config, no setup"""
    cache_key = tuple(sorted(services))
    
    # Return cached result if available
    if cache_key in _gateway_cache:
        cached = _gateway_cache[cache_key]
        return cached['gateway_url'], cached['access_token']
    
    # If not cached, do one-time setup
    try:
        config = setup_gateway_once(services)
        return config['gateway_url'], config['access_token']
    except Exception as e:
        print(f"Error getting gateway config for UI: {e}")
        # Fallback to hardcoded URL if setup fails
        return 'https://demos3smithyv3-vibgmhi7zd.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp', None

# Service target configurations
SERVICE_TARGETS = {
    's3': {
        'name': 'DemoSmithytargetForS3',
        'uri': 's3://agentcore-gateway-search-us-east-1/s3-apis.json',
        'description': 'Smithy Target for S3 APIs'
    },
    'lambda': {
        'name': 'DemoSmithytargetForLambda',
        'uri': 's3://agentcore-gateway-search-us-east-1/lambda-apis.json', 
        'description': 'Smithy Target for Lambda APIs'
    },
    'eks': {
        'name': 'DemoSmithytargetForEKS',
        'uri': 's3://agentcore-gateway-search-us-east-1/eks-apis.json',
        'description': 'Smithy Target for EKS APIs'
    },
    'cloudwatch': {
        'name': 'DemoSmithytargetForCloudWatch',
        'uri': 's3://agentcore-gateway-search-us-east-1/cloudwatch-logs-apis.json',
        'description': 'Smithy Target for CloudWatch APIs'
    }
}

def create_target_config(service_uri):
    """Create target configuration for a service"""
    return {
        "mcp": {
            "smithyModel": {
                "s3": {
                    "uri": service_uri
                }
            }
        }
    }

def setup_gateway_targets(gateway_client, gateway_id, services=None):
    """Setup gateway targets for specified services"""
    if services is None:
        services = ['s3']  # Default to S3 only
    
    credential_config = {
        "credentialProviderType": "GATEWAY_IAM_ROLE"
    }
    
    created_targets = []
    
    for service in services:
        if service not in SERVICE_TARGETS:
            print(f"Warning: Service '{service}' not configured, skipping")
            continue
            
        target_info = SERVICE_TARGETS[service]
        target_config = create_target_config(target_info['uri'])
        
        target_id = utils.get_or_create_gateway_target(
            gateway_client,
            gateway_id,
            target_info['name'],
            target_config,
            credential_config
        )
        
        created_targets.append({
            'service': service,
            'target_id': target_id,
            'name': target_info['name']
        })
        
    return created_targets

def setup_gateway(services=None):
    """Create or retrieve gateway and return configuration"""
    boto_session = Session()
    region = boto_session.region_name or os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    
    gateway_name = f'agentcore-gateway-{region}'
    
    # Cognito configuration
    USER_POOL_NAME = "sample-agentcore-gateway-pool"
    RESOURCE_SERVER_ID = "sample-agentcore-gateway-id"
    RESOURCE_SERVER_NAME = "sample-agentcore-gateway-name"
    CLIENT_NAME = "sample-agentcore-gateway-client"
    SCOPES = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Write access"}
    ]
    scope_string = f"{RESOURCE_SERVER_ID}/gateway:read {RESOURCE_SERVER_ID}/gateway:write"
    
    print(f"Setting up gateway: {gateway_name}")
    
    # Setup Cognito
    cognito = boto3.client("cognito-idp", region_name=region)
    user_pool_id = utils.get_or_create_user_pool(cognito, USER_POOL_NAME)
    utils.get_or_create_resource_server(cognito, user_pool_id, RESOURCE_SERVER_ID, RESOURCE_SERVER_NAME, SCOPES)
    client_id, client_secret = utils.get_or_create_m2m_client(cognito, user_pool_id, CLIENT_NAME, RESOURCE_SERVER_ID)
    
    # Setup IAM role
    agentcore_gateway_iam_role = utils.create_agentcore_gateway_role_s3_smithy("sample-lambdagateway")
    
    # Setup gateway
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    auth_config = {
        "customJWTAuthorizer": { 
            "allowedClients": [client_id],
            "discoveryUrl": f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
        }
    }
    
    gateway_info = utils.get_or_create_gateway(
        gateway_client, 
        gateway_name, 
        agentcore_gateway_iam_role['Role']['Arn'], 
        auth_config
    )
    
    # Setup S3 bucket and Smithy schemas before creating targets
    print("Setting up S3 bucket and Smithy schemas...")
    if not utils.setup_smithy_schemas(region):
        print("Warning: Failed to setup Smithy schemas, continuing anyway...")
    
    # Setup gateway targets for specified services
    targets = setup_gateway_targets(gateway_client, gateway_info['gatewayId'], services)
    
    # Get access token
    token_response = utils.get_token(user_pool_id, client_id, client_secret, scope_string, region)
    
    return {
        'gateway_url': gateway_info['gatewayUrl'],
        'gateway_id': gateway_info['gatewayId'],
        'access_token': token_response["access_token"],
        'region': region,
        'targets': targets
    }

def get_gateway_url(services=None):
    """Get gateway URL - main function for other modules to use"""
    try:
        config = setup_gateway(services)
        return config['gateway_url']
    except Exception as e:
        print(f"Error getting gateway URL: {e}")
        # Fallback to hardcoded URL if setup fails
        return 'https://demos3smithyv3-vibgmhi7zd.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'

def get_gateway_config(services=None):
    """Get complete gateway configuration"""
    return setup_gateway(services)

def get_gateway_url_for_ui(services=['s3', 'lambda', 'eks', 'cloudwatch']):
    """Get gateway URL and token for UI - lightweight version without testing"""
    try:
        config = setup_gateway(services)
        return config['gateway_url'], config['access_token']
    except Exception as e:
        print(f"Error getting gateway config for UI: {e}")
        # Fallback to hardcoded URL if setup fails
        return 'https://demos3smithyv3-vibgmhi7zd.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp', None

def add_service_target(service, name, uri, description):
    """Add a new service target configuration"""
    SERVICE_TARGETS[service] = {
        'name': name,
        'uri': uri, 
        'description': description
    }
