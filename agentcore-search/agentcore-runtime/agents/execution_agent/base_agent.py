#!/usr/bin/env python3
"""
Base Agent - Common functionality for all agents with fix tracking
"""

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient, MCPAgentTool
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool as MCPTool
import json
import requests
import boto3
import os
import sys
from typing import Dict, List, Optional
from fix_action import FixAction, FixResult

# Add gateway utils and config
#sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'gateway'))
import utils
from gateway_config import get_gateway_config

class BaseAgent:
    def __init__(self, use_semantic_search=True):
        self.use_semantic_search = use_semantic_search
        self.fixes_applied = []  # Track fixes applied during this session
        
        # Get dynamic gateway configuration
        try:
            from ui_config import get_gateway_config_for_ui
            self.gateway_url, self.jwt_token = get_gateway_config_for_ui()
        except Exception as e:
            print(f"Failed to get gateway config: {e}")
            # Fallback to hardcoded values
            self.gateway_url = 'https://demos3smithyv3-vibgmhi7zd.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
            self.jwt_token = self._get_jwt_token_fallback()
        
        self.client = MCPClient(
            lambda: streamablehttp_client(
                self.gateway_url, headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
        )
        self.model = BedrockModel(
            model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            temperature=0.1,
            max_tokens=131000
        )
    
    def log_fix_action(self, action_type: str, resource_type: str, resource_identifier: str,
                      description: str, commands_executed: List[str], before_state: Dict,
                      after_state: Dict, success: bool, error_message: Optional[str] = None) -> FixAction:
        """Log a fix action performed by the agent"""
        fix_action = FixAction.create_new(
            action_type=action_type,
            resource_type=resource_type,
            resource_identifier=resource_identifier,
            description=description,
            commands_executed=commands_executed,
            before_state=before_state,
            after_state=after_state,
            success=success,
            error_message=error_message
        )
        
        self.fixes_applied.append(fix_action)
        print(f"🔧 Fix logged: {fix_action.get_summary()}")
        return fix_action
    
    def get_fix_result(self, validation_suggestions: List[str] = None) -> FixResult:
        """Get the result of all fixes applied during this session"""
        return FixResult.from_fixes(self.fixes_applied, validation_suggestions)
    
    def clear_fixes(self):
        """Clear the fixes applied list (for new requests)"""
        self.fixes_applied = []
    
    def _get_jwt_token_fallback(self):
        """Fallback JWT token method (legacy)"""
        try:
            REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
            USER_POOL_NAME = "sample-agentcore-gateway-pool"
            RESOURCE_SERVER_ID = "sample-agentcore-gateway-id"
            CLIENT_NAME = "sample-agentcore-gateway-client"
            scopeString = f"{RESOURCE_SERVER_ID}/gateway:read {RESOURCE_SERVER_ID}/gateway:write"
            
            cognito = boto3.client("cognito-idp", region_name=REGION)
            user_pool_id = utils.get_or_create_user_pool(cognito, USER_POOL_NAME)
            client_id, client_secret = utils.get_or_create_m2m_client(cognito, user_pool_id, CLIENT_NAME, RESOURCE_SERVER_ID)
            
            token_response = utils.get_token(user_pool_id, client_id, client_secret, scopeString, REGION)
            return token_response["access_token"]
        except Exception as e:
            print(f"Failed to get JWT token: {e}")
            return None
    
    def tool_search(self, query):
        """Search for relevant tools using semantic search"""
        toolParams = {
            "name": "x_amz_bedrock_agentcore_search",
            "arguments": {"query": query},
        }
        
        requestBody = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": toolParams,
        }
        
        try:
            response = requests.post(
                self.gateway_url,
                json=requestBody,
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Content-Type": "application/json",
                },
            )
            
            # If 401, try to refresh token
            if response.status_code == 401:
                print("Token expired, refreshing...")
                try:
                    from ui_config import refresh_access_token
                    new_token = refresh_access_token()
                    if new_token:
                        self.jwt_token = new_token
                        # Retry with new token
                        response = requests.post(
                            self.gateway_url,
                            json=requestBody,
                            headers={
                                "Authorization": f"Bearer {self.jwt_token}",
                                "Content-Type": "application/json",
                            },
                        )
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    return []
            
            result = response.json()
            
            # Handle different response formats
            if "result" in result and "content" in result["result"]:
                tools = result["result"]["content"][0]["text"]
            elif "content" in result:
                tools = result["content"][0]["text"]
            else:
                print(f"Unexpected response format: {result}")
                return []
            
            parsed_tools = json.loads(tools)
            return parsed_tools["tools"]
            
        except (KeyError, json.JSONDecodeError, requests.RequestException) as e:
            print(f"Error in tool search: {e}")
            return []
    
    def _refresh_mcp_client(self):
        """Refresh MCP client with new token"""
        try:
            from ui_config import refresh_access_token
            new_token = refresh_access_token()
            if new_token:
                self.jwt_token = new_token
                self.client = MCPClient(
                    lambda: streamablehttp_client(
                        self.gateway_url, headers={"Authorization": f"Bearer {self.jwt_token}"}
                    )
                )
                return True
        except Exception as e:
            print(f"Failed to refresh MCP client: {e}")
        return False
    
    def get_all_tools(self):
        """Get all tools from gateway (lightweight versions)"""
        try:
            with self.client:
                more_tools = True
                tools = []
                pagination_token = None
                
                while more_tools:
                    tmp_tools = self.client.list_tools_sync(pagination_token=pagination_token)
                    tools.extend(tmp_tools)
                    if tmp_tools.pagination_token is None:
                        more_tools = False
                    else:
                        more_tools = True
                        pagination_token = tmp_tools.pagination_token
                
                # Create lightweight versions
                filtered_tools = []
                for tool in tools:
                    if len(tool.tool_name) > 64:
                        continue
                    if tool.tool_name == "DemoSmithytargetForS3___PutBucketMetricsConfiguration":
                        continue
                    
                    lightweight_mcp_tool = MCPTool(
                        name=tool.mcp_tool.name,
                        description=tool.mcp_tool.description,
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    )
                    lightweight_agent_tool = MCPAgentTool(lightweight_mcp_tool, self.client)
                    filtered_tools.append(lightweight_agent_tool)
                
                return filtered_tools
        
        except Exception as e:
            # If client initialization failed, try refreshing token
            if "client initialization failed" in str(e) or "401" in str(e):
                print("MCP client failed, attempting token refresh...")
                if self._refresh_mcp_client():
                    try:
                        # Retry with refreshed client
                        with self.client:
                            more_tools = True
                            tools = []
                            pagination_token = None
                            
                            while more_tools:
                                tmp_tools = self.client.list_tools_sync(pagination_token=pagination_token)
                                tools.extend(tmp_tools)
                                if tmp_tools.pagination_token is None:
                                    more_tools = False
                                else:
                                    more_tools = True
                                    pagination_token = tmp_tools.pagination_token
                            
                            filtered_tools = []
                            for tool in tools:
                                if len(tool.tool_name) > 64:
                                    continue
                                if tool.tool_name == "DemoSmithytargetForS3___PutBucketMetricsConfiguration":
                                    continue
                                
                                lightweight_mcp_tool = MCPTool(
                                    name=tool.mcp_tool.name,
                                    description=tool.mcp_tool.description,
                                    inputSchema={
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                )
                                lightweight_agent_tool = MCPAgentTool(lightweight_mcp_tool, self.client)
                                filtered_tools.append(lightweight_agent_tool)
                            
                            return filtered_tools
                    except Exception as retry_e:
                        print(f"Retry also failed: {retry_e}")
                        return []
                else:
                    print("Token refresh failed")
                    return []
            else:
                print(f"MCP client error: {e}")
                return []
    
    def tools_to_strands_mcp_tools(self, tools, top_n=10):
        """Convert search results to Strands MCPAgentTool objects"""
        strands_mcp_tools = []
        for tool in tools[:top_n]:
            mcp_tool = MCPTool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
            )
            strands_mcp_tools.append(MCPAgentTool(mcp_tool, self.client))
        return strands_mcp_tools
    
    def tools_to_strands_mcp_tools(self, tools, top_n=10):
        """Convert search results to Strands MCPAgentTool objects"""
        strands_mcp_tools = []
        for tool in tools[:top_n]:
            mcp_tool = MCPTool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
            )
            strands_mcp_tools.append(MCPAgentTool(mcp_tool, self.client))
        return strands_mcp_tools
