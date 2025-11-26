#!/usr/bin/env python3
"""
Documentation Agent - Provides guidance when tools are missing
"""

from base_agent import BaseAgent
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class DocumentationAgent(BaseAgent):
    def __init__(self, use_semantic_search=True):
        super().__init__(use_semantic_search)
    
    def provide_documentation(self, user_request, intent, execution_response=None):
        """Provide documentation and guidance when tools are missing"""
        print(f"📚 Documentation Agent activated")
        
        doc_prompt = f"""
        The user requested: "{user_request}"
        
        {f"Previous response indicated: {execution_response}" if execution_response else ""}
        
        Since the required tools are not available in the current gateway, provide:
        1. Explanation of what tools/permissions would be needed
        2. Relevant AWS documentation links
        3. Step-by-step guidance for manual implementation
        4. Alternative approaches if available
        
        Be helpful and provide actionable guidance even without direct tool access.
        """
        
        # Use lightweight agent for documentation
        doc_agent = Agent(model=self.model, tools=[])
        return doc_agent(doc_prompt)

@app.entrypoint
def invoke(payload):
    """AgentCore Runtime entry point"""
    user_input = payload.get("prompt", "Hello")
    
    # Create and use the agent
    agent = DocumentationAgent(use_semantic_search=True)
    result = agent.provide_documentation(
        user_request=user_input,
        intent={"service": "documentation"}
    )
    
    # Return response
    if hasattr(result, 'message'):
        return result.message['content'][0]['text']
    else:
        return str(result)

if __name__ == "__main__":
    app.run()
