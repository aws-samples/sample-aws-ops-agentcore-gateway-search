#!/usr/bin/env python3
"""
Validation Agent - Verifies fixes applied by other agents
"""

from base_agent import BaseAgent
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from fix_action import FixAction, FixResult
from typing import List

app = BedrockAgentCoreApp()

class ValidationAgent(BaseAgent):
    def __init__(self, use_semantic_search=True):
        super().__init__(use_semantic_search)
    
    def validate_fixes(self, fixes_to_validate: List[FixAction], context_text=""):
        """Validate that applied fixes are working correctly"""
        print(f"✅ Validation Agent activated")
        
        # Clear previous fixes for new validation
        self.clear_fixes()
        
        if not fixes_to_validate:
            return {
                'result': "No fixes to validate",
                'validation_results': [],
                'all_validated': True
            }
        
        tools_info = {}
        
        if self.use_semantic_search:
            # Search for validation tools
            search_query = "validate check status describe get configuration"
            tools_found = self.tool_search(search_query)
            tools = self.tools_to_strands_mcp_tools(tools_found, 15)
            print(f"📊 Using {len(tools)} semantic search tools for validation")
            
            tools_info = {
                'semantic_search_used': True,
                'search_query': search_query,
                'tools_found': [tool.get('name', 'Unknown') for tool in tools_found[:10]],
                'tools_count': len(tools)
            }
        else:
            tools = self.get_all_tools()
            print(f"📊 Using ALL {len(tools)} available tools for validation")
            
            tools_info = {
                'semantic_search_used': False,
                'total_tools': len(tools),
                'tools_count': len(tools)
            }
        
        # Build validation request
        validation_request = self._build_validation_request(fixes_to_validate, context_text)
        
        system_prompt = """You are an AWS validation specialist.
        
        Your role is to verify that fixes applied by other agents are working correctly:
        1. Check the current state of resources that were modified
        2. Verify that the fixes resolved the original issues
        3. Ensure no new issues were introduced
        4. Test functionality to confirm proper operation
        5. Report validation status for each fix
        
        For each fix validation:
        - Use appropriate AWS tools to check current resource state
        - Compare with the expected after-state from the fix
        - Test functionality where possible
        - Report PASS/FAIL with detailed reasoning
        
        Be thorough and accurate in your validation."""
        
        with self.client:
            agent = Agent(
                model=self.model,
                tools=tools,
                system_prompt=system_prompt
            )
            
            result = agent(validation_request)
            
            # Process validation results
            validation_results = self._process_validation_results(fixes_to_validate, result)
            
            return {
                'result': result,
                'tools_info': tools_info,
                'validation_results': validation_results,
                'all_validated': all(v['status'] == 'PASS' for v in validation_results)
            }
    
    def _build_validation_request(self, fixes: List[FixAction], context_text: str) -> str:
        """Build validation request from fix actions"""
        request = context_text + "\n" if context_text else ""
        request += "Please validate the following fixes that were applied:\n\n"
        
        for i, fix in enumerate(fixes, 1):
            request += f"{i}. {fix.description}\n"
            request += f"   Resource: {fix.resource_identifier}\n"
            request += f"   Action: {fix.action_type}\n"
            request += f"   Commands: {', '.join(fix.commands_executed)}\n"
            request += f"   Expected state: {fix.after_state}\n\n"
        
        request += "For each fix, please:\n"
        request += "1. Check the current state of the resource\n"
        request += "2. Verify it matches the expected after-state\n"
        request += "3. Test functionality if applicable\n"
        request += "4. Report PASS or FAIL with reasoning\n"
        
        return request
    
    def _process_validation_results(self, fixes: List[FixAction], agent_result) -> List[dict]:
        """Process agent validation results into structured format"""
        validation_results = []
        
        for fix in fixes:
            # Simple validation result structure
            # In a real implementation, you'd parse the agent's response more intelligently
            validation_results.append({
                'fix_id': fix.action_id,
                'resource': fix.resource_identifier,
                'status': 'PENDING',  # Would be determined by parsing agent response
                'message': f"Validation pending for {fix.description}",
                'timestamp': fix.timestamp
            })
        
        return validation_results

@app.entrypoint
def invoke(payload):
    """AgentCore Runtime entry point"""
    user_input = payload.get("prompt", "Hello")
    conversation_history = payload.get("conversation_history", [])
    fix_id = payload.get("fix_id", None)
    
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
    agent = ValidationAgent(use_semantic_search=True)
    result = agent.validate_fixes(
        fixes_to_validate=[],  # Empty list as placeholder
        context_text=f"User request: {user_input}\nValidation type: fix"
    )
    
    # Return response
    if isinstance(result, dict):
        return result.get('result', str(result))
    else:
        return str(result)

if __name__ == "__main__":
    app.run()
