import streamlit as st
import asyncio
import nest_asyncio
from google.genai import types

# Import your agent components
from agent import runner, initialize_session_for_app

# Fix asyncio loop for Streamlit
nest_asyncio.apply()

st.set_page_config(page_title="GreenEvent AI", page_icon="🌱")
st.title("🌱 GreenEvent AI Orchestrator")

# --- Constants ---
USER_ID = "streamlit_user"
SESSION_ID = "hackathon_demo_v1"

# --- Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize the agent session once
if "agent_initialized" not in st.session_state:
    asyncio.run(initialize_session_for_app(SESSION_ID, USER_ID))
    st.session_state.agent_initialized = True
    # Add an initial greeting
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I am your Sustainable Event Orchestrator. Tell me about your upcoming event."})

# --- Display Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Helper to Run Agent ---
async def run_agent(new_input=None):
    """Runs the ADK runner and handles the stream."""
    
    # If this is a resumption (approval), use the stored payload
    if new_input is None and "pending_confirmation" in st.session_state:
        # Construct the ADK function response
        tool_data = st.session_state.pending_confirmation
        confirmation_payload = {
            "confirmed": st.session_state.approval_status  # True or False
        }
        
        # Create the complex Types object required by ADK
        new_input = types.Content(
            role="user",
            parts=[types.Part(
                function_response=types.FunctionResponse(
                    name=tool_data["tool_name"],
                    id=tool_data["tool_id"],
                    response=confirmation_payload
                )
            )]
        )
        # Clear the pending state
        del st.session_state.pending_confirmation
        del st.session_state.approval_status

    # If this is a normal user text input
    elif isinstance(new_input, str):
        new_input = types.Content(role="user", parts=[types.Part(text=new_input)])

    # Call the runner
    response_stream = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=new_input
    )

    # Process Stream
    assistant_response_text = ""
    placeholder = st.empty()
    
    async for event in response_stream:
        # 1. Handle Text Responses
        if event.content and event.content.parts:
            text_chunk = event.content.parts[0].text
            if text_chunk:
                assistant_response_text += text_chunk
                placeholder.markdown(assistant_response_text + "▌")
        
        # 2. Handle Confirmation Requests (The LRO)
        if event.adk_request_confirmation:
            req = event.adk_request_confirmation
            st.session_state.pending_confirmation = {
                "tool_name": req.tool_name,
                "tool_id": req.tool_call_id,
                "hint": req.hint
            }
            st.rerun() # Stop everything and refresh to show buttons

    # Finalize display
    placeholder.markdown(assistant_response_text)
    if assistant_response_text:
        st.session_state.messages.append({"role": "assistant", "content": assistant_response_text})


# --- Handle Pending Approval (The Button) ---
if "pending_confirmation" in st.session_state:
    with st.chat_message("assistant"):
        st.warning(f"✋ Approval Required: {st.session_state.pending_confirmation['hint']}")
        col1, col2 = st.columns(2)
        if col1.button("✅ Approve"):
            st.session_state.approval_status = True
            asyncio.run(run_agent()) # Resume execution
            st.rerun()
        if col2.button("❌ Reject"):
            st.session_state.approval_status = False
            asyncio.run(run_agent()) # Resume execution
            st.rerun()

# --- Handle User Input ---
# Only show input if we are NOT waiting for an approval
elif prompt := st.chat_input("Plan a 2-day workshop in Berlin..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        asyncio.run(run_agent(prompt))