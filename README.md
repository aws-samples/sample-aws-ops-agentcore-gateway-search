# AgentCore Gateway Multi-Agent System

A multi-agent AWS operations system using Amazon Bedrock AgentCore with semantic search capabilities.

## ⚠️ Important Disclaimers

**This is a code sample for demonstration purposes only. Do not use in production environments without proper security review, testing, and hardening.**

**Responsible AI:** This system includes automated AWS operations capabilities. Users are responsible for ensuring appropriate safeguards, monitoring, and human oversight when deploying AI-driven infrastructure management tools.

## Project Overview

This project demonstrates:
- Multi-agent orchestration with AgentCore Runtime
- Dynamic gateway integration with semantic search
- Automated AWS operations through natural language
- Conversational AI with context preservation

## AgentCore Semantic Search

This project leverages **Amazon Bedrock AgentCore's semantic search capabilities** to enhance tool selection and intelligent curation across the multi-agent system.

### What is AgentCore Semantic Search?

AgentCore semantic search enables intelligent tool curation through vector-based similarity matching. When `enable_semantic_search=True` is configured on the Gateway, the system automatically:

- **Curates relevant tools** from large API catalogs based on user intent
- **Prevents tool overload** that can cause agent hallucinations and incorrect tool selections
- **Improves agent responses** by finding the most relevant tools for each request
- **Reduces noise** by filtering out irrelevant operations from extensive API specifications

**Built-in Search Tool**: Gateway provides a special `x_amz_bedrock_agentcore_search` tool accessible via standard MCP operations for intelligent tool discovery at scale.

### Implementation in This Project

**Gateway Integration:**
```python
gateway = client.setup_gateway(
    gateway_name="aws-operations",
    target_source=json.dumps(api_config),
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config'],
    target_type='openapi',
    enable_semantic_search=True,  # Enables intelligent tool curation
    description="AWS operations gateway with semantic tool selection"
)
```

### Benefits in Multi-Agent Operations

1. **Intelligent Tool Selection**: From hundreds of AWS API operations, semantic search identifies the most relevant tools for each user request
2. **Enhanced Agent Coordination**: Agents receive curated, contextually relevant tools rather than overwhelming API catalogs
3. **Improved User Experience**: More accurate responses through better tool selection and reduced irrelevant operations
4. **Scalable API Integration**: Handles large API specifications efficiently by surfacing only relevant operations

### Semantic Search Workflow

1. **User Request**: "My Lambda function has performance issues"
2. **Semantic Analysis**: Gateway identifies performance-related AWS operations from API catalog
3. **Tool Curation**: Returns Lambda monitoring, CloudWatch metrics, and performance tuning tools
4. **Agent Processing**: Agents receive focused, relevant tools instead of entire AWS API catalog
5. **Targeted Response**: More precise solutions using semantically-matched operations

This semantic approach enables the system to understand intent rather than relying on exact keyword matches, making the multi-agent system more intelligent and responsive to user needs.

## Architecture

**6 Specialized Agents:**
- Intent Classifier: Routes user requests
- Troubleshooting Agent: Handles AWS service failures
- Execution Agent: Manages normal AWS operations  
- Validation Agent: Verifies applied changes
- Documentation Agent: Provides AWS documentation
- Orchestrator: Coordinates all agents

**Supporting Infrastructure:**
- AgentCore Gateway with semantic search
- Cognito authentication
- S3 storage for API schemas
- Demo scenarios for testing

## Prerequisites

### Required Files Setup
**Download AWS API Definitions:**
```bash
# Create smithy directory
mkdir -p agentcore-search/smithy/api-definitions

# Download required API definition files from AWS API models repository
# Visit: https://github.com/aws/api-models-aws/tree/main/models
# Download these files to agentcore-search/smithy/api-definitions/:
# - s3-apis.json (from s3/service/2006-03-01/s3-2006-03-01.json)
# - lambda-apis.json (from lambda/service/2015-03-31/lambda-2015-03-31.json)  
# - eks-apis.json (from eks/service/2017-11-01/eks-2017-11-01.json)
# - cloudwatch-logs-apis.json (from cloudwatch-logs/service/2014-03-28/cloudwatch-logs-2014-03-28.json)
```

### AWS Account Requirements
- AWS CLI configured
- Access to Amazon Bedrock AgentCore
- Region: us-east-1

### Required AWS Permissions
- Bedrock AgentCore (runtime, control)
- IAM (roles, policies)
- ECR (repositories)
- SSM (parameters)
- CloudWatch (logs)
- Cognito (user pools)
- S3 (buckets)
- Lambda (functions)
- CodeBuild (projects)

### Local Environment
```bash
python3 --version  # 3.10+
pip install streamlit strands boto3 requests mcp
```

## Deployment Steps

### Step 1: Clone and Setup
```bash
git clone <repository-url>
cd agentcore-samples/agentcore-search
export AWS_DEFAULT_REGION=us-east-1
```

### Step 2: Deploy Gateway Infrastructure
```bash
cd gateway
python3 gateway_setup.py
```

This creates:
- AgentCore Gateway
- Cognito user pool for authentication
- S3 bucket for API schemas
- Configuration file saved to `config/`

### Step 3: Deploy AgentCore Runtime Agents
```bash
cd ../agentcore-runtime/agents
python3 deploy_all_agents.py
```

This deploys:
- 6 agents to AgentCore Runtime
- ECR repositories for container images
- IAM roles with required permissions
- SSM parameters for agent discovery

**Note:** Deployment takes approximately 35 minutes.

### Step 4: Configure Agent Permissions
```bash
python3 update_agent_permissions.py
```

This configures:
- Orchestrator permissions to invoke sub-agents
- SSM parameter access for agent discovery

### Step 5: Create Demo Scenarios (Optional)
```bash
cd ../../demo_scenarios

# Create test resources
python3 run_scenario.py lambda      # Lambda function with issues
python3 run_scenario.py s3          # S3 bucket with security gaps
python3 run_scenario.py cloudwatch  # Missing monitoring setup
```

### Step 6: Launch User Interface
```bash
cd ../agentcore-runtime
streamlit run multi_agent_runtime_app.py --server.port 8502
```

Access the UI at: `http://localhost:8502`

## Testing the System

### Basic Operations
1. Open UI at `http://localhost:8502`
2. Verify agent status shows "Runtime Ready"
3. Enter: `"List my S3 buckets"`
4. Review response and tools used

### Automated Fixes
1. Enter: `"My Lambda function agentcore-demo-lambda-perf has performance issues"`
2. Agent identifies and applies fixes automatically
3. Check "Fixes Applied" tab for audit trail

### Conversational Flow
1. Ask: `"What Lambda functions do I have?"`
2. Follow up: `"Check the first one for issues"`
3. Agent maintains context between requests

## User Interface Features

**4-Tab Interface:**
- Response: Agent responses and actions
- Tools Used: Semantic search information
- Fixes Applied: Automated changes with audit trail
- Metrics: Response times and success rates

**Agent Status Sidebar:**
- Real-time connectivity for all 6 agents
- Dynamic ARN retrieval from SSM

## Troubleshooting

### Agent Deployment Issues
```bash
# Check specific agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-name}-DEFAULT --follow

# Redeploy specific agent
python3 deploy_all_agents.py --agent {agent_name}
```

### Gateway Authentication Problems
```bash
# Refresh authentication tokens
cd gateway
python3 -c "from ui_config import refresh_access_token; refresh_access_token()"
```

### Permission Errors
```bash
# Update orchestrator permissions
python3 update_agent_permissions.py
```

### UI Connection Issues
- Check agent status in sidebar
- Verify all agents show "Runtime Ready"
- Restart UI if needed

## Resource Cleanup

### Complete Cleanup
```bash
python3 cleanup_workshop_resources.py
```

### Selective Cleanup
```bash
# Clean specific components
python3 cleanup_workshop_resources.py --service agentcore
python3 cleanup_workshop_resources.py --service gateway
python3 cleanup_workshop_resources.py --service scenarios
```

### Preview Changes
```bash
python3 cleanup_workshop_resources.py --dry-run
```

## Project Structure

```
agentcore-search/
├── agentcore-runtime/              # AgentCore Runtime deployment
│   ├── agents/                     # Agent implementations
│   │   ├── deploy_all_agents.py    # Deployment automation
│   │   ├── orchestrator/           # Main coordinator agent
│   │   ├── intent_classifier/      # Request routing
│   │   ├── troubleshooting_agent/  # Issue resolution
│   │   ├── execution_agent/        # AWS operations
│   │   ├── validation_agent/       # Change verification
│   │   └── documentation_agent/    # AWS documentation
│   └── multi_agent_runtime_app.py  # Streamlit interface
├── gateway/                        # Gateway infrastructure
│   ├── gateway_setup.py            # Setup script
│   ├── utils.py                    # AWS utilities
│   └── config/                     # Runtime configuration
├── demo_scenarios/                 # Test scenarios
│   ├── run_scenario.py             # Scenario runner
│   ├── lambda_performance_scenario.py
│   ├── s3_security_scenario.py
│   └── cloudwatch_monitoring_scenario.py
├── smithy/                         # API schemas
└── cleanup_workshop_resources.py   # Resource cleanup
```

## Key Components

**AgentCore Gateway:**
- Semantic search with `enable_semantic_search=True` for intelligent tool curation
- JWT authentication with Cognito OAuth integration
- Multi-service API integration (S3, Lambda, EKS, CloudWatch)
- MCP (Model Context Protocol) endpoint for agent framework integration

**Multi-Agent System:**
- Hub-and-spoke communication pattern
- Session-based conversation management
- Automated fix application with audit trails

**Demo Scenarios:**
- Real AWS resources with intentional issues
- Lambda performance problems
- S3 security configurations
- CloudWatch monitoring gaps

## Next Steps

After deployment:
1. Test basic operations through the UI
2. Try automated fix scenarios
3. Explore conversational capabilities
4. Review audit trails and logs
5. Clean up resources when finished
