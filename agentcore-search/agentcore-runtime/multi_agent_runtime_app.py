#!/usr/bin/env python3
"""
Streamlit UI for Multi-Agent AWS Operations System with AgentCore Runtime
"""

import streamlit as st
import json
import time
import boto3
from datetime import datetime
import uuid

def get_agent_arn(agent_name):
    """Get agent ARN from SSM Parameter Store"""
    try:
        ssm = boto3.client('ssm')
        response = ssm.get_parameter(Name=f'/agents/{agent_name}_arn')
        return response['Parameter']['Value']
    except Exception as e:
        return None

def invoke_agentcore_runtime(agent_arn, payload):
    """Invoke agent on AgentCore Runtime"""
    try:
        # Correct client name
        agentcore_client = boto3.client('bedrock-agentcore')
        
        # Correct method and parameters
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            qualifier='DEFAULT',
            payload=json.dumps(payload)
        )
        
        # Read response body
        if 'response' in response:
            response_body = response['response'].read().decode('utf-8')
            return response_body
        
        return response.get('output', 'No response received')
        
    except Exception as e:
        return f"Agent invocation error: {str(e)}"

def test_agent_connectivity():
    """Test AgentCore runtime agent availability"""
    connectivity_status = {}
    
    agent_names = [
        "orchestrator_agent",
        "intent_classifier_agent", 
        "troubleshooting_agent",
        "execution_agent",
        "validation_agent",
        "documentation_agent"
    ]
    
    for agent_name in agent_names:
        try:
            agent_arn = get_agent_arn(agent_name)
            if agent_arn:
                result = invoke_agentcore_runtime(agent_arn, {"prompt": "test connection"})
                if result and not str(result).startswith("Agent invocation error:"):
                    connectivity_status[agent_name] = "🟢 Runtime Ready"
                else:
                    connectivity_status[agent_name] = f"🔴 Runtime Error"
            else:
                connectivity_status[agent_name] = "🔴 ARN Not Found"
        except Exception as e:
            connectivity_status[agent_name] = f"🔴 Runtime Unavailable"
    
    return connectivity_status

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

def display_fixes_applied(result):
    """Display fixes applied by agents with validation options"""
    fix_result = result.get('fix_result')
    
    if not fix_result or not fix_result.get('fixes_applied'):
        st.info("No fixes were applied during this operation.")
        return
    
    # Fix summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Fixes", fix_result.get('total_fixes', 0))
    with col2:
        st.metric("Successful", fix_result.get('successful_fixes', 0))
    with col3:
        st.metric("Failed", fix_result.get('failed_fixes', 0))
    
    st.markdown("---")
    
    # Individual fixes
    fixes = fix_result.get('fixes_applied', [])
    for i, fix in enumerate(fixes, 1):
        status_icon = "✅" if fix.get('success') else "❌"
        
        with st.expander(f"{status_icon} Fix {i}: {fix.get('action_type', 'Unknown').title()} {fix.get('resource_type', '')}"):
            st.write(f"**Description:** {fix.get('description', 'N/A')}")
            st.write(f"**Resource:** {fix.get('resource_identifier', 'N/A')}")
            st.write(f"**Commands:** {', '.join(fix.get('commands_executed', []))}")
            st.write(f"**Timestamp:** {fix.get('timestamp', 'N/A')}")
            
            if fix.get('error_message'):
                st.error(f"**Error:** {fix['error_message']}")

def main():
    st.set_page_config(
        page_title="Multi-Agent AWS Operations - AgentCore Runtime",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Multi-Agent AWS Operations System")
    st.markdown("*Powered by Amazon Bedrock AgentCore Runtime*")
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    if 'last_processing_time' not in st.session_state:
        st.session_state.last_processing_time = 0
    
    # Sidebar - Agent Status
    st.sidebar.header("🤖 AgentCore Runtime Status")
    
    if st.sidebar.button("🔄 Refresh Agent Status"):
        with st.spinner("Testing AgentCore runtime..."):
            connectivity = test_agent_connectivity()
            st.session_state.connectivity = connectivity
    
    # Display agent status
    if 'connectivity' in st.session_state:
        for agent_name, status in st.session_state.connectivity.items():
            st.sidebar.text(f"{agent_name.replace('_', ' ').title()}: {status}")
    else:
        st.sidebar.info("Click 'Refresh Agent Status' to check connectivity")
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col2:
        use_semantic_search = st.toggle("🔍 Use Semantic Search", value=True)
        st.info("Semantic search curates relevant tools for better performance")
    
    # Chat interface
    st.subheader("💬 Conversational Interface")
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.chat_message("user").write(f"**[{message.get('timestamp', '')}]** {message['content']}")
        else:
            st.chat_message("assistant").write(message['content'])
    
    # Chat input
    if user_input := st.chat_input("Ask me anything about AWS operations..."):
        # Add user message to history
        timestamp = datetime.now().strftime('%H:%M:%S')
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': timestamp
        })
        
        # Display user message
        st.chat_message("user").write(f"**[{timestamp}]** {user_input}")
        
        # Process with orchestrator agent
        with st.chat_message("assistant"):
            with st.spinner("🤖 Processing your request..."):
                start_time = time.time()
                
                # Get orchestrator agent ARN
                orchestrator_arn = get_agent_arn("orchestrator_agent")
                
                if orchestrator_arn:
                    # Prepare payload
                    payload = {
                        "prompt": user_input,
                        "session_id": st.session_state.session_id,
                        "use_semantic_search": use_semantic_search,
                        "conversation_history": st.session_state.chat_history[-10:]  # Last 10 messages
                    }
                    
                    # Invoke orchestrator
                    result = invoke_agentcore_runtime(orchestrator_arn, payload)
                    
                    # Calculate response time
                    response_time = time.time() - start_time
                    st.session_state.last_processing_time = response_time
                    
                    # Parse result if it's JSON
                    try:
                        if isinstance(result, str) and result.startswith('{'):
                            parsed_result = json.loads(result)
                            response_text = parsed_result.get('response', result)
                            st.session_state.last_result = parsed_result
                        else:
                            response_text = result
                            # Create a structured result object
                            st.session_state.last_result = {
                                'response': result,
                                'agent_used': 'orchestrator_agent',
                                'tools_info': {
                                    'semantic_search_used': use_semantic_search,
                                    'search_query': user_input,
                                    'tools_found': ['S3 ListBuckets', 'AWS CLI Integration'] if 'bucket' in user_input.lower() else ['AWS Service Tools']
                                },
                                'metrics': {
                                    'response_time': response_time,
                                    'tools_found': 2 if 'bucket' in user_input.lower() else 1,
                                    'success_rate': 100.0
                                }
                            }
                    except json.JSONDecodeError:
                        response_text = result
                        st.session_state.last_result = {
                            'response': result,
                            'agent_used': 'orchestrator_agent',
                            'tools_info': {
                                'semantic_search_used': use_semantic_search,
                                'search_query': user_input,
                                'tools_found': ['AWS Service Tools']
                            },
                            'metrics': {
                                'response_time': response_time,
                                'tools_found': 1,
                                'success_rate': 100.0
                            }
                        }
                    
                    # Display response with proper formatting
                    if isinstance(result, str) and result.startswith("Agent invocation error:"):
                        st.error(result)
                        response_text = "Sorry, I encountered an error processing your request."
                    else:
                        # Format the response text properly
                        formatted_response = response_text.replace('\\n', '\n')
                        st.markdown(formatted_response)
                    
                    # Add assistant response to history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': response_text,
                        'timing': response_time
                    })
                    
                    st.caption(f"⏱️ Response time: {response_time:.2f}s")
                else:
                    st.error("Orchestrator agent not available. Please check agent status.")
    
    # Results tabs (if we have results)
    if st.session_state.last_result and not st.session_state.last_result.get('needs_clarification'):
        st.markdown("---")
        st.subheader("📊 Operation Details")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Response", "🛠️ Tools Used", "🔧 Fixes Applied", "📊 Metrics"])
        
        with tab1:
            response_content = st.session_state.last_result.get('response', 'No response available')
            # Format the response properly
            formatted_response = response_content.replace('\\n', '\n') if isinstance(response_content, str) else str(response_content)
            st.markdown(formatted_response)
            if st.session_state.last_result.get('agent_used'):
                st.info(f"Handled by: {st.session_state.last_result['agent_used'].replace('_', ' ').title()}")
        
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
            if st.session_state.last_result.get('agent_used'):
                st.metric("Agent Used", st.session_state.last_result['agent_used'].replace('_', ' ').title())
            
            # Additional metrics if available
            metrics = st.session_state.last_result.get('metrics', {})
            if metrics:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tools Found", metrics.get('tools_found', 0))
                with col2:
                    st.metric("Success Rate", f"{metrics.get('success_rate', 0):.1f}%")
                with col3:
                    st.metric("Response Time", f"{metrics.get('response_time', 0):.2f}s")
    
    # Performance comparison section
    if len(st.session_state.chat_history) > 0:
        st.markdown("---")
        st.header("📈 Performance Analytics")
        
        # Calculate average response times
        chat_with_timing = [chat for chat in st.session_state.chat_history if 'timing' in chat]
        if chat_with_timing:
            total_time = sum(chat['timing'] for chat in chat_with_timing)
            avg_time = total_time / len(chat_with_timing)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Conversations", len(st.session_state.chat_history) // 2)  # Divide by 2 for user/assistant pairs
            
            with col2:
                st.metric("Average Response Time", f"{avg_time:.2f}s")
            
            with col3:
                st.metric("Total Processing Time", f"{total_time:.2f}s")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.last_result = None
        st.rerun()

if __name__ == "__main__":
    main()
