#!/usr/bin/env python3
"""
Multi-Agent Orchestrator - Coordinates all agents with conversation support
"""

from intent_classifier import IntentClassifier
from troubleshooting_agent import TroubleshootingAgent
from execution_agent import ExecutionAgent
from documentation_agent import DocumentationAgent
from validation_agent import ValidationAgent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import time

app = BedrockAgentCoreApp()

class MultiAgentOrchestrator:
    def __init__(self, use_semantic_search=True):
        self.use_semantic_search = use_semantic_search
        self.intent_classifier = IntentClassifier(use_semantic_search)
        self.troubleshooting_agent = TroubleshootingAgent(use_semantic_search)
        self.execution_agent = ExecutionAgent(use_semantic_search)
        self.documentation_agent = DocumentationAgent(use_semantic_search)
        self.validation_agent = ValidationAgent(use_semantic_search)
    
    def _build_context_text(self, conversation_history):
        """Build context text from conversation history"""
        if not conversation_history:
            return ""
        
        context = "Previous conversation context:\n"
        for turn in conversation_history:
            context += f"User: {turn.user_message}\n"
            context += f"Assistant: {turn.agent_response[:200]}...\n"
        context += "\nCurrent request (consider the above context):\n"
        return context
    
    def _extract_fix_info(self, result, agent_used):
        """Extract fix information from agent result"""
        if isinstance(result, dict) and 'fix_result' in result:
            return result['fix_result']
        elif hasattr(result, 'fix_result'):
            return result.fix_result
        return None
    
    def _extract_tools_info(self, result, agent_used):
        """Extract tool information from agent result"""
        if isinstance(result, dict) and 'tools_info' in result:
            return result['tools_info']
        return {}
    
    def _extract_response_text(self, result):
        """Extract response text from any agent result format"""
        try:
            # Handle execution agent format: {'result': AgentResult, 'tools_missing': bool}
            if isinstance(result, dict) and 'result' in result:
                agent_result = result['result']
                if hasattr(agent_result, 'message'):
                    return agent_result.message['content'][0]['text']
                return str(agent_result)
            # Handle direct agent result
            elif hasattr(result, 'message'):
                return result.message['content'][0]['text']
            return str(result)
        except Exception as e:
            return f"Error extracting response: {str(e)}"
    
    def orchestrate_conversation(self, user_request: str, session_id: str = "default"):
        """Main orchestration with conversation support"""
        print(f"\n🎯 Orchestrator processing: '{user_request}' (Session: {session_id})")
        print(f"🔍 Semantic Search: {'ENABLED' if self.use_semantic_search else 'DISABLED'}")
        
        start_time = time.time()
        
        # Step 1: Classify intent with context
        print("🧠 Intent Classifier analyzing request...")
        intent_start = time.time()
        intent = self.intent_classifier.classify_with_context(user_request, session_id)
        intent_time = time.time() - intent_start
        
        print(f"   Intent: {intent.get('intent_category', 'UNKNOWN')} (confidence: {intent.get('confidence', 'unknown')}) - {intent_time:.2f}s")
        
        # Handle clarification requests
        if intent.get('needs_clarification'):
            response = {
                'response': intent['clarification_question'],
                'agent_used': 'intent_classifier',
                'total_time': time.time() - start_time,
                'needs_clarification': True,
                'session_id': session_id
            }
            return response
        
        # Route to appropriate agent
        agent_start = time.time()
        agent_used = ""
        
        try:
            # Get conversation history for context
            conversation_history = self.intent_classifier._get_conversation_history(session_id, last_n=3)
            context_text = self._build_context_text(conversation_history)
            
            if intent['intent_category'] == 'TROUBLESHOOTING':
                print("🔧 Routing to Troubleshooting Agent...")
                agent_used = "troubleshooting_agent"
                result = self.troubleshooting_agent.troubleshoot(user_request, intent, context_text)
            elif intent['intent_category'] == 'EXECUTION':
                print("⚡ Routing to Execution Agent...")
                agent_used = "execution_agent"
                exec_result = self.execution_agent.execute(user_request, intent, context_text)
                
                # Ensure exec_result is a dictionary
                if not isinstance(exec_result, dict):
                    raise ValueError(f"Execution agent returned unexpected type: {type(exec_result)}")
                
                # Check if tools were missing and route to documentation
                if exec_result.get("tools_missing"):
                    print("📚 Tools missing - routing to Documentation Agent")
                    agent_used = "documentation_agent"
                    doc_result = self.documentation_agent.provide_documentation(user_request)
                    # Preserve tools_info from execution agent
                    result = {
                        'result': doc_result,
                        'tools_info': exec_result.get('tools_info', {})
                    }
                else:
                    result = exec_result
            else:
                print("📚 Routing to Documentation Agent...")
                agent_used = "documentation_agent"
                result = self.documentation_agent.provide_documentation(user_request)
            
            agent_time = time.time() - agent_start
            total_time = time.time() - start_time
            
            print(f"   Agent Response Time: {agent_time:.2f}s")
            print(f"   Total Time: {total_time:.2f}s")
            
            # Extract response text from result
            response_text = self._extract_response_text(result)
            
            # Extract tool information
            tools_info = self._extract_tools_info(result, agent_used)
            
            # Extract fix information
            fix_result = self._extract_fix_info(result, agent_used)
            
            # Add to conversation history
            self.intent_classifier.add_conversation_turn(
                session_id, user_request, response_text, agent_used
            )
            
            return {
                'response': response_text,
                'agent_used': agent_used,
                'intent': intent,
                'total_time': total_time,
                'agent_time': agent_time,
                'intent_time': intent_time,
                'session_id': session_id,
                'needs_clarification': False,
                'tools_info': tools_info,
                'fix_result': fix_result,
                'requires_validation': fix_result.requires_validation if fix_result else False
            }
            
        except Exception as e:
            print(f"❌ Error in agent execution: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"Sorry, I encountered an error: {str(e)}",
                'agent_used': agent_used if 'agent_used' in locals() else 'unknown',
                'intent': intent if 'intent' in locals() else {},
                'total_time': time.time() - start_time,
                'session_id': session_id,
                'needs_clarification': False,
                'error': True
            }
    
    def orchestrate(self, user_request):
        """Original orchestrate method for backward compatibility"""
        result = self.orchestrate_conversation(user_request)
        return result['response']

@app.entrypoint
def invoke(payload):
    """AgentCore Runtime entry point"""
    # Parse payload if it's a string
    if isinstance(payload, str):
        import json
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"prompt": payload}
    
    user_input = payload.get("prompt", "Hello")
    session_id = payload.get("session_id", "default")
    conversation_history = payload.get("conversation_history", [])
    
    # Convert conversation history to expected format
    class ConversationTurn:
        def __init__(self, user_msg, agent_resp):
            self.user_message = user_msg
            self.agent_response = agent_resp
    
    formatted_history = []
    for turn in conversation_history:
        if isinstance(turn, dict):
            formatted_history.append(
                ConversationTurn(
                    turn.get('user_message', ''),
                    turn.get('agent_response', '')
                )
            )
    
    # Create and use the orchestrator
    orchestrator = MultiAgentOrchestrator(use_semantic_search=True)
    result = orchestrator.orchestrate_conversation(user_input, "default")
    
    # Return response
    if isinstance(result, dict):
        return result.get('response', str(result))
    else:
        return str(result)

if __name__ == "__main__":
    app.run()
