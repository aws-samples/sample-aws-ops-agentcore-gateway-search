#!/usr/bin/env python3
"""
Streamlit UI for Multi-Agent AWS Operations System with Conversational Chat
"""

import streamlit as st
import json
import sys
import os
import time
from datetime import datetime
import uuid

# Add multi_agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))
from orchestrator import MultiAgentOrchestrator

def display_fixes_applied(result):
    """Display fixes applied by agents with validation options"""
    fix_result = result.get('fix_result')
    
    if not fix_result or not fix_result.fixes_applied:
        st.info("No fixes were applied during this operation.")
        return
    
    # Fix summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Fixes", fix_result.total_fixes)
    with col2:
        st.metric("Successful", fix_result.successful_fixes)
    with col3:
        st.metric("Failed", fix_result.failed_fixes)
    
    st.markdown("---")
    
    # Individual fixes
    for i, fix in enumerate(fix_result.fixes_applied, 1):
        status_icon = "✅" if fix.success else "❌"
        
        with st.expander(f"{status_icon} Fix {i}: {fix.action_type.title()} {fix.resource_type}"):
            # Fix details
            st.write(f"**Description:** {fix.description}")
            st.write(f"**Resource:** {fix.resource_identifier}")
            st.write(f"**Commands:** {', '.join(fix.commands_executed)}")
            st.write(f"**Timestamp:** {fix.timestamp}")
            
            if fix.error_message:
                st.error(f"**Error:** {fix.error_message}")
            
            # Before/After states
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Before State:**")
                if fix.before_state:
                    st.json(fix.before_state)
                else:
                    st.write("No before state recorded")
            
            with col2:
                st.write("**After State:**")
                if fix.after_state:
                    st.json(fix.after_state)
                else:
                    st.write("No after state recorded")
            
            # Validation button
            if fix.success:
                if st.button(f"🔍 Validate Fix {fix.action_id}", key=f"validate_{fix.action_id}"):
                    validate_fix(fix.action_id, fix)
    
    # Validation suggestions
    if fix_result.validation_suggestions:
        st.markdown("---")
        st.subheader("💡 Validation Suggestions")
        for suggestion in fix_result.validation_suggestions:
            st.write(f"• {suggestion}")
    
    # Validate all fixes button
    if fix_result.successful_fixes > 0:
        st.markdown("---")
        if st.button("🔍 Validate All Fixes", key="validate_all"):
            validate_all_fixes(fix_result.fixes_applied)

def process_validation_request(validation_request):
    """Process validation request and convert to user input"""
    if validation_request['type'] == 'single':
        fix_action = validation_request['fix_action']
        return f"Please validate the fix applied to {fix_action.resource_identifier}: {fix_action.description}"
    elif validation_request['type'] == 'all':
        fixes = validation_request['fixes']
        fix_descriptions = [f"{fix.resource_identifier}: {fix.description}" for fix in fixes]
        return f"Please validate all {len(fixes)} fixes that were applied: " + "; ".join(fix_descriptions)
    
    return "Please validate the recent fixes"

def validate_fix(fix_id, fix_action):
    """Validate a specific fix"""
    st.info(f"Validating fix {fix_id}...")
    # Store validation request in session state for processing
    if 'validation_requests' not in st.session_state:
        st.session_state.validation_requests = []
    
    st.session_state.validation_requests.append({
        'type': 'single',
        'fix_id': fix_id,
        'fix_action': fix_action,
        'timestamp': datetime.now().isoformat()
    })
    
    st.success(f"Validation request queued for fix {fix_id}")

def validate_all_fixes(fixes):
    """Validate all successful fixes"""
    successful_fixes = [fix for fix in fixes if fix.success]
    st.info(f"Validating {len(successful_fixes)} successful fixes...")
    
    # Store validation request in session state for processing
    if 'validation_requests' not in st.session_state:
        st.session_state.validation_requests = []
    
    st.session_state.validation_requests.append({
        'type': 'all',
        'fixes': successful_fixes,
        'timestamp': datetime.now().isoformat()
    })
    
    st.success(f"Validation request queued for all {len(successful_fixes)} fixes")

def format_tools_info(tools_info):
    """Format tools information for display"""
    if not tools_info:
        return "No tools information available"
    
    if tools_info.get('semantic_search_used'):
        search_query = tools_info.get('search_query', 'Unknown')
        tools_found = tools_info.get('tools_found', [])
        
        result = f"**🔍 Semantic Search Query:** `{search_query}`\n\n"
        result += f"**📊 Tools Found:** {len(tools_found)} tools\n\n"
        
        if tools_found:
            result += "**🛠️ Top Tools Returned:**\n"
            for i, tool in enumerate(tools_found[:10], 1):
                if isinstance(tool, str):
                    result += f"{i}. `{tool}`\n"
                else:
                    result += f"{i}. `{tool.get('name', 'Unknown')}`\n"
                    if tool.get('description'):
                        result += f"   *{tool['description'][:100]}...*\n"
        
        return result
    else:
        total_tools = tools_info.get('total_tools', 0)
        return f"**⚠️ Using ALL Tools:** {total_tools} lightweight tools (no semantic search)"

def initialize_session_state():
    """Initialize session state variables"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'orchestrator_with_search' not in st.session_state:
        st.session_state.orchestrator_with_search = MultiAgentOrchestrator(use_semantic_search=True)
    if 'orchestrator_without_search' not in st.session_state:
        st.session_state.orchestrator_without_search = MultiAgentOrchestrator(use_semantic_search=False)
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    if 'last_processing_time' not in st.session_state:
        st.session_state.last_processing_time = 0
    if 'validation_requests' not in st.session_state:
        st.session_state.validation_requests = []

def add_to_chat_history(user_message, response, agent_used, timing, needs_clarification=False, tools_info=None, fix_result=None):
    """Add conversation turn to chat history"""
    st.session_state.chat_history.append({
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'user_message': user_message,
        'response': response,
        'agent_used': agent_used,
        'timing': timing,
        'needs_clarification': needs_clarification,
        'tools_info': tools_info or {},
        'fix_result': fix_result
    })

def display_chat_history():
    """Display chat conversation history"""
    for i, chat in enumerate(st.session_state.chat_history):
        # User message
        with st.chat_message("user"):
            st.write(f"**[{chat['timestamp']}]** {chat['user_message']}")
        
        # Agent response
        with st.chat_message("assistant"):
            if chat['needs_clarification']:
                st.warning(f"🤔 **Clarification needed:** {chat['response']}")
            else:
                st.write(chat['response'])
                
                # Show agent info in expander
                with st.expander(f"Agent Details - {chat['agent_used']} ({chat['timing']:.2f}s)"):
                    st.info(f"**Agent:** {chat['agent_used']}")
                    st.info(f"**Response Time:** {chat['timing']:.2f}s")

def main():
    st.set_page_config(
        page_title="AWS Multi-Agent Conversational Assistant",
        page_icon="🤖",
        layout="wide"
    )
    
    initialize_session_state()
    
    st.title("🤖 AWS Multi-Agent Conversational Assistant")
    st.markdown("**Semantic Search Demo with Multi-Turn Conversations**")
    
    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Semantic search toggle
        use_semantic_search = st.toggle(
            "🔍 Enable Semantic Search", 
            value=True,
            help="Toggle between semantic search (curated tools) vs all tools"
        )
        
        st.markdown("---")
        st.header("📊 Session Info")
        st.info(f"**Session ID:** {st.session_state.session_id}")
        st.info(f"**Conversation Turns:** {len(st.session_state.chat_history)}")
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation"):
            st.session_state.chat_history = []
            st.session_state.session_id = str(uuid.uuid4())[:8]
            st.rerun()
        
        st.markdown("---")
        st.header("🚀 Quick Actions")
        
        quick_actions = [
            "List all S3 buckets in my account",
            "Why is my Lambda function failing?",
            "Create an EKS cluster",
            "Help me troubleshoot CloudWatch logs"
        ]
        
        for action in quick_actions:
            if st.button(action, key=f"quick_{action}"):
                st.session_state.pending_message = action
    
    # Main chat interface
    st.header("💬 Conversation")
    
    # Display chat history
    if st.session_state.chat_history:
        display_chat_history()
    else:
        st.info("👋 Start a conversation by asking about AWS services, troubleshooting, or operations!")
    
    # Chat input
    user_input = st.chat_input("Ask me about AWS operations, troubleshooting, or any questions...")
    
    # Handle quick action clicks
    if hasattr(st.session_state, 'pending_message'):
        user_input = st.session_state.pending_message
        delattr(st.session_state, 'pending_message')
    
    # Process validation requests
    if st.session_state.validation_requests:
        validation_request = st.session_state.validation_requests.pop(0)
        user_input = process_validation_request(validation_request)
    
    # Process user input
    if user_input:
        # Show user message immediately
        with st.chat_message("user"):
            st.write(f"**[{datetime.now().strftime('%H:%M:%S')}]** {user_input}")
        
        # Process with orchestrator
        with st.spinner("🤖 Processing your request..."):
            start_time = time.time()
            
            # Select orchestrator based on semantic search setting
            orchestrator = (st.session_state.orchestrator_with_search 
                          if use_semantic_search 
                          else st.session_state.orchestrator_without_search)
            
            # Get response with conversation context
            result = orchestrator.orchestrate_conversation(
                user_input, 
                st.session_state.session_id
            )
            
            processing_time = time.time() - start_time
            
            # Store result in session state
            st.session_state.last_result = result
            st.session_state.last_processing_time = processing_time
        
        # Display response in chat
        with st.chat_message("assistant"):
            if result.get('needs_clarification'):
                st.warning(f"🤔 **Clarification needed:** {result['response']}")
            else:
                st.success(result['response'])
        
        # Add to chat history
        if result.get('needs_clarification'):
            add_to_chat_history(
                user_input, 
                result['response'], 
                result['agent_used'], 
                processing_time,
                needs_clarification=True,
                tools_info=result.get('tools_info', {}),
                fix_result=result.get('fix_result')
            )
        else:
            add_to_chat_history(
                user_input, 
                result['response'], 
                result['agent_used'], 
                processing_time,
                tools_info=result.get('tools_info', {}),
                fix_result=result.get('fix_result')
            )
        
        st.rerun()
    
    # Show tabs for last result (outside input processing)
    if st.session_state.last_result and not st.session_state.last_result.get('needs_clarification'):
        st.markdown("---")
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Response", "🛠️ Tools Used", "🔧 Fixes Applied", "📊 Metrics"])
        
        with tab1:
            st.write(st.session_state.last_result['response'])
        
        with tab2:
            st.subheader("Tools Information")
            tools_info = st.session_state.last_result.get('tools_info', {})
            st.markdown(format_tools_info(tools_info))
        
        with tab3:
            st.subheader("Fixes Applied")
            display_fixes_applied(st.session_state.last_result)
        
        with tab4:
            st.subheader("Performance Metrics")
            st.metric("Total Time", f"{st.session_state.last_processing_time:.2f}s")
            st.metric("Agent Used", st.session_state.last_result['agent_used'])
    
    # Performance comparison section
    if len(st.session_state.chat_history) > 0:
        st.markdown("---")
        st.header("📈 Performance Analytics")
        
        # Calculate average response times
        total_time = sum(chat['timing'] for chat in st.session_state.chat_history)
        avg_time = total_time / len(st.session_state.chat_history)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Conversations", len(st.session_state.chat_history))
        
        with col2:
            st.metric("Average Response Time", f"{avg_time:.2f}s")
        
        with col3:
            st.metric("Total Processing Time", f"{total_time:.2f}s")

if __name__ == "__main__":
    main()
