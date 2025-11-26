#!/usr/bin/env python3
"""
Execution Agent - Handles normal AWS operations
"""

from base_agent import BaseAgent
from strands import Agent

class ExecutionAgent(BaseAgent):
    def __init__(self, use_semantic_search=True):
        super().__init__(use_semantic_search)
    
    def execute(self, user_request, intent, context_text=""):
        """Handle normal AWS operations with conversation context and proactive fixes"""
        print(f"⚙️ Execution Agent activated with proactive fixes")
        
        # Clear previous fixes for new request
        self.clear_fixes()
        
        # Build request with context
        full_request = context_text + user_request if context_text else user_request
        
        tools_info = {}
        
        if self.use_semantic_search:
            # Search for execution tools
            search_query = f"{intent.get('aws_service', '')} {user_request}"
            tools_found = self.tool_search(search_query)
            tools = self.tools_to_strands_mcp_tools(tools_found, 10)
            print(f"📊 Using {len(tools)} semantic search tools")
            
            # Capture tools info for UI - extract just names and count
            tool_names = [tool.get('name', 'Unknown') for tool in tools_found[:10]]
            tools_info = {
                'semantic_search_used': True,
                'search_query': search_query,
                'tools_found': tool_names,
                'tools_count': len(tools)
            }
        else:
            # Use all available tools
            tools = self.get_all_tools()
            print(f"📊 Using ALL {len(tools)} available tools")
            
            # Capture tools info for UI
            tools_info = {
                'semantic_search_used': False,
                'total_tools': len(tools),
                'tools_count': len(tools)
            }
        
        system_prompt = """You are an AWS operations specialist with conversation memory and proactive fix capabilities.
        
        For execution requests:
        1. Consider the conversation context provided - remember previous interactions
        2. If the user refers to previous results (like "show more", "yes", "continue"), use that context
        3. Identify the specific AWS operation needed
        4. Use appropriate tools to complete the task
        5. PROACTIVELY IDENTIFY AND FIX issues during operations:
           - Optimize resource configurations when suboptimal
           - Fix permission issues that prevent operations
           - Update deprecated settings automatically
           - Apply security best practices
        6. Provide clear results and status
        7. Log any fixes applied during the operation
        8. If tools are not available, clearly state what's missing
        
        IMPORTANT:
        - Maintain conversation context across interactions
        - Be proactive in identifying optimization opportunities
        - Apply safe fixes automatically during normal operations
        - Always explain what optimizations were made
        
        Be efficient, accurate, and proactive in your operations while maintaining conversation memory."""
        
        with self.client:
            agent = Agent(
                model=self.model,
                tools=tools,
                system_prompt=system_prompt
            )
            
            result = agent(full_request)
            
            # Check if tools were missing
            response_text = result.message['content'][0]['text']
            tools_missing = any(phrase in response_text.lower() for phrase in ['not available', 'cannot find', 'missing', 'no tools', 'not supported'])
            
            # Get fix results from this execution session
            fix_result = self.get_fix_result([
                "Verify the operation completed successfully",
                "Check if any optimizations were applied",
                "Confirm resource configurations are optimal"
            ])
            
            return {
                "result": result, 
                "tools_missing": tools_missing,
                "tools_info": tools_info,
                "fix_result": fix_result
            }
