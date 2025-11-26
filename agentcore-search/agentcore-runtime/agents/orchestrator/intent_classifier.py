#!/usr/bin/env python3
"""
Intent Classifier Agent - Routes requests to appropriate agents with conversation support
"""

from base_agent import BaseAgent
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

app = BedrockAgentCoreApp()
from datetime import datetime

@dataclass
class ConversationTurn:
    user_message: str
    agent_response: str
    agent_used: str
    timestamp: str

class IntentClassifier(BaseAgent):
    def __init__(self, use_semantic_search=True):
        super().__init__(use_semantic_search)
        self.conversations = {}  # session_id -> List[ConversationTurn]
        self.pending_clarifications = {}  # session_id -> clarification_data
    
    def classify_with_context(self, user_request: str, session_id: str = "default") -> Dict:
        """Classify with conversation context and clarification support"""
        
        # Check for pending clarifications
        if session_id in self.pending_clarifications:
            return self._handle_clarification_response(user_request, session_id)
        
        # Get conversation history
        history = self._get_conversation_history(session_id, last_n=3)
        
        # Build context-aware classification
        result = self._classify_with_history(user_request, history)
        
        # Check if clarification needed
        if self._needs_clarification(result, user_request):
            clarification = self._generate_clarification(user_request, result)
            self.pending_clarifications[session_id] = {
                'original_request': user_request,
                'clarification': clarification,
                'suggested_agent': result.get('intent_category', 'EXECUTION')
            }
            return {
                'intent_category': 'CLARIFICATION',
                'needs_clarification': True,
                'clarification_question': clarification,
                'confidence': 'low'
            }
        
        return result
    
    def classify(self, user_request):
        """Original classify method for backward compatibility"""
        return self.classify_with_context(user_request)
    
    def add_conversation_turn(self, session_id: str, user_message: str, agent_response: str, agent_used: str):
        """Add a turn to conversation history"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        turn = ConversationTurn(
            user_message=user_message,
            agent_response=agent_response,
            agent_used=agent_used,
            timestamp=datetime.now().isoformat()
        )
        self.conversations[session_id].append(turn)
    
    def _get_conversation_history(self, session_id: str, last_n: int = 3) -> List[ConversationTurn]:
        """Get recent conversation history"""
        return self.conversations.get(session_id, [])[-last_n:]
    
    def _classify_with_history(self, user_request: str, history: List[ConversationTurn]) -> Dict:
        """Classify request with conversation context"""
        context = ""
        if history:
            context = "Previous conversation:\n"
            for turn in history:
                context += f"User: {turn.user_message}\nAgent ({turn.agent_used}): {turn.agent_response[:100]}...\n"
            context += "\n"
        
        classification_prompt = f"""
        {context}Current request: "{user_request}"
        
        Classify this AWS request considering the conversation context:
        
        TROUBLESHOOTING: Problem-solving queries about failures, errors, issues, debugging, "why", "failing", "not working"
        EXECUTION: Normal operations like list, create, describe, delete, configure
        
        Return only JSON:
        {{
            "intent_category": "TROUBLESHOOTING|EXECUTION",
            "aws_service": "service_name_or_unknown",
            "confidence": "high|medium|low",
            "reasoning": "brief explanation"
        }}
        """
        
        classifier_agent = Agent(model=self.model, tools=[])
        result = classifier_agent(classification_prompt)
        
        try:
            response_text = result.message['content'][0]['text']
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]
            return json.loads(json_str)
        except:
            # Fallback with context awareness
            if any(word in user_request.lower() for word in ['fail', 'error', 'issue', 'problem', 'why', 'debug', 'troubleshoot']):
                return {"intent_category": "TROUBLESHOOTING", "aws_service": "unknown", "confidence": "medium"}
            else:
                return {"intent_category": "EXECUTION", "aws_service": "unknown", "confidence": "medium"}
    
    def _needs_clarification(self, result: Dict, user_request: str) -> bool:
        """Determine if clarification is needed"""
        confidence = result.get('confidence', 'high')
        ambiguous_keywords = ['help', 'maybe', 'could', 'might', 'not sure']
        
        return (confidence == 'low' or 
                len(user_request.split()) < 4 or
                any(keyword in user_request.lower() for keyword in ambiguous_keywords))
    
    def _generate_clarification(self, user_request: str, classification: Dict) -> str:
        """Generate clarifying question"""
        clarification_prompt = f"""
        User request: "{user_request}"
        Classification: {classification}
        
        Generate a helpful clarifying question to better understand the user's AWS task.
        Be specific about services, actions, or resources. Keep it concise.
        """
        
        classifier_agent = Agent(model=self.model, tools=[])
        result = classifier_agent(clarification_prompt)
        
        try:
            response = result.message['content'][0]['text']
            return response.strip()
        except:
            return "Could you provide more details about what AWS service or action you'd like help with?"
    
    def _handle_clarification_response(self, user_response: str, session_id: str) -> Dict:
        """Handle user's response to clarification"""
        pending = self.pending_clarifications[session_id]
        enhanced_request = f"{pending['original_request']} {user_response}"
        
        # Clear pending clarification
        del self.pending_clarifications[session_id]
        
        # Re-classify with enhanced context
        return self._classify_with_history(enhanced_request, self._get_conversation_history(session_id))

@app.entrypoint
def invoke(payload):
    """AgentCore Runtime entry point"""
    user_input = payload.get("prompt", "Hello")
    session_id = payload.get("session_id", "default")
    conversation_history = payload.get("conversation_history", [])
    
    # Create and use the agent
    agent = IntentClassifier(use_semantic_search=True)
    result = agent.classify_with_conversation(
        user_request=user_input,
        session_id=session_id
    )
    
    # Return response
    return result

if __name__ == "__main__":
    app.run()
