#!/usr/bin/env python3
"""
Troubleshooting Agent - Handles AWS service failures and errors
"""

from base_agent import BaseAgent
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class TroubleshootingAgent(BaseAgent):
    def __init__(self, use_semantic_search=True):
        super().__init__(use_semantic_search)
    
    def troubleshoot(self, user_request, intent, context_text=""):
        """Handle troubleshooting scenarios with auto-fix capabilities"""
        print(f"🔧 Troubleshooting Agent activated with auto-fix")
        
        # Clear previous fixes for new request
        self.clear_fixes()
        
        # Build request with context
        full_request = context_text + user_request if context_text else user_request
        
        tools_info = {}
        
        if self.use_semantic_search:
            # Refined search query - focus on specific log analysis tools
            aws_service = intent.get('aws_service', '')
            search_query = f"{aws_service} get function configuration filter log events get log events describe log groups"
            tools_found = self.tool_search(search_query)
            tools = self.tools_to_strands_mcp_tools(tools_found, 15)
            print(f"📊 Using {len(tools)} semantic search tools")
            
            # Capture tools info for UI
            tools_info = {
                'semantic_search_used': True,
                'search_query': search_query,
                'tools_found': tools_found,
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
        
        system_prompt = """You are an AWS troubleshooting specialist with conversation memory and auto-fix capabilities.
        
        For troubleshooting requests:
        1. Consider the conversation context provided - remember previous interactions
        2. If the user refers to previous issues or results, use that context
        3. Identify the AWS service and specific resource with issues
        4. Check service configuration and status
        5. Analyze CloudWatch logs for errors
        6. Identify root causes
        7. AUTOMATICALLY APPLY FIXES when safe and appropriate:
           - Update configurations (memory, timeout, environment variables)
           - Fix IAM permissions and policies
           - Restart or redeploy resources when needed
           - Update resource settings for optimization
        8. Log each fix action clearly with before/after states
        9. Provide validation steps for the user to verify fixes
        
        IMPORTANT: 
        - Maintain conversation context across interactions
        - Always explain what you're fixing and why
        - Show before and after states for transparency
        - Only apply fixes that are safe and reversible
        - Ask for confirmation before destructive operations
        
        Be thorough in diagnosis, maintain conversation memory, and proactive in applying fixes."""
        
        with self.client:
            agent = Agent(
                model=self.model, 
                tools=tools,
                system_prompt=system_prompt
            )
            result = agent(full_request)
            
            # Get fix results from this troubleshooting session
            fix_result = self.get_fix_result([
                "Verify the issue has been resolved",
                "Check system performance after fixes",
                "Monitor for any side effects"
            ])
            
            return {
                'result': result,
                'tools_info': tools_info,
                'fix_result': fix_result
            }

@app.entrypoint
def invoke(payload):
    """AgentCore Runtime entry point"""
    user_input = payload.get("prompt", "Hello")
    conversation_history = payload.get("conversation_history", [])
    
    # Build context from history
    context_text = ""
    if conversation_history:
        context_text = "Previous conversation context:\n"
        for turn in conversation_history:
            if isinstance(turn, dict):
                context_text += f"User: {turn.get('user_message', '')}\n"
                context_text += f"Assistant: {turn.get('agent_response', '')[:200]}...\n"
        context_text += "\nCurrent request (consider the above context):\n"
    
    # Create and use the agent
    agent = TroubleshootingAgent(use_semantic_search=True)
    result = agent.troubleshoot(
        user_request=user_input,
        intent={"aws_service": "lambda"},
        context_text=context_text
    )
    
    # Return response
    if isinstance(result, dict):
        return result.get('result', str(result))
    else:
        return str(result)

if __name__ == "__main__":
    app.run()
