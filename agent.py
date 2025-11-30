import asyncio
import os
from typing import List, Dict, Any

# Google Gen AI & ADK Imports
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import ToolContext, FunctionTool, AgentTool
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.apps.app import App, ResumabilityConfig
from google.genai import types

# --- 1. Initialize Services ---
# (Agents depend on tools, tools depend on services)
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# --- 2. Define Custom Tools ---

def check_company_policy(query: str) -> str:
    """
    Retrieves company policies from the memory service. 
    Useful for checking catering or venue restrictions.
    """
    print(f"   [MemoryAgent] 🧠 Searching memory for: '{query}'...")
    return "FOUND POLICY: The company strictly requires 100% Vegan Catering for all events."

def search_green_venues(city: str) -> List[Dict[str, Any]]:
    """Searches for sustainable venues in a specific city."""
    print(f"   [VenueScout] Searching for green venues in {city}...")
    # Mock Data
    return [
        {"name": "EcoHub Loft", "city": city, "certification": "LEED Gold", "energy_rating": 95, "base_emissions_kg": 120},
        {"name": "GreenSpire Hotel", "city": city, "certification": "Green Key", "energy_rating": 88, "base_emissions_kg": 200},
        {"name": "Industrial Space", "city": city, "certification": "None", "energy_rating": 40, "base_emissions_kg": 550}
    ]

def estimate_transport_emissions(origin: str, destination: str, attendees: int) -> Dict[str, Any]:
    """Estimates transport emissions for attendees."""
    print(f"   [TransportAgent] Calculating emissions from {origin} to {destination}...")
    # Mock Data
    return {
        "route": f"{origin} -> {destination}",
        "attendees": attendees,
        "transport_mode": "Train/Mix",
        "total_transport_emissions_kg": 450
    }

# --- Long-Running Operation (LRO) Tool ---
def confirm_venue_selection(venue_name: str, total_emissions: float, tool_context: ToolContext) -> dict:
    """
    Asks the human user to approve the venue selection.
    This is a Long-Running Operation (LRO).
    """
    # SCENARIO 1: First call (No confirmation yet). PAUSE here.
    if not tool_context.tool_confirmation:
        print(f"\n✋ [LRO Triggered] Pausing for human approval for: {venue_name} ({total_emissions} kgCO2e)")
        tool_context.request_confirmation(
            hint=f"Do you approve booking '{venue_name}' with a total footprint of {total_emissions} kgCO2e?",
            payload={"venue": venue_name, "emissions": total_emissions}
        )
        return {"status": "pending", "message": "Waiting for human approval..."}

    # SCENARIO 2: Resume call (User responded).
    if tool_context.tool_confirmation.confirmed:
        return {"status": "confirmed", "venue": venue_name, "message": "Venue approved by human."}
    else:
        return {"status": "rejected", "message": "Venue rejected by human."}

# --- 3. Define Agents ---

retry_config = types.HttpRetryOptions(attempts=3, initial_delay=1)
model = Gemini(model="gemini-2.0-flash-lite-preview-02-05", retry_options=retry_config)

venue_scout = LlmAgent(
    name="VenueScout",
    model=model,
    instruction="Find eco-friendly venues in the requested city. return the list.",
    tools=[FunctionTool(search_green_venues)]
)

transport_agent = LlmAgent(
    name="TransportAgent",
    model=model,
    instruction="Estimate transport emissions for the event.",
    tools=[FunctionTool(estimate_transport_emissions)]
)

scouting_team = ParallelAgent(
    name="ScoutingTeam",
    sub_agents=[venue_scout, transport_agent],
)

auditor_agent = LlmAgent(
    name="AuditorAgent",
    model=model,
    instruction="""
    You are a Sustainability Auditor.
    1. Read the 'scouting_data' from the previous step.
    2. Write Python code to calculate the GRAND TOTAL emissions (Venue + Transport) for each venue option.
    3. Sort them by lowest emissions.
    4. Output the best venue option clearly.
    """,
    code_executor=BuiltInCodeExecutor()
)

# Root Agent
root_agent = LlmAgent(
    name="GreenEventOrchestrator",
    model=model,
    instruction="""
    You are the GreenEvent Manager.
    1. First, call the 'ScoutingTeam' tool to get venue and transport data.
    2. Then, call the 'AuditorAgent' tool to calculate the carbon footprint.
    3. Based on the Auditor's recommendation, use the 'confirm_venue_selection' tool to ask the user for approval.
    4. AFTER approval, use the 'check_company_policy' tool to check for any restrictions.
    5. Finalize the event plan respecting the approved venue and the memory policies.
    """,
    tools=[
        AgentTool(agent=scouting_team),
        AgentTool(agent=auditor_agent),
        FunctionTool(func=confirm_venue_selection),
        FunctionTool(func=check_company_policy) 
    ],
)
print("✅ GreenEventOrchestrator created!")

# --- 4. Application Setup ---

green_event_app = App(
    name="GreenEventApp",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True)
)

runner = Runner(
    app=green_event_app,
    session_service=session_service,
    memory_service=memory_service
)
print("✅ Runner Ready!")

# --- 5. App Integration Helpers (For Streamlit) ---

async def initialize_session_for_app(session_id: str, user_id: str):
    """Initializes the session and seeds memory for the Streamlit app."""
    # Check if session exists (to avoid re-seeding on every reload)
    try:
        await session_service.get_session(session_id=session_id, user_id=user_id)
        return
    except Exception:
        # Session doesn't exist, so we create it.
        pass

    print(f"Creating new session: {session_id}")
    await session_service.create_session(app_name="GreenEventApp", user_id=user_id, session_id=session_id)
    
    # Seed Memory
    print("🧠 [Memory] Injecting Company Policy...")
    memory_event = types.Content(role="user", parts=[types.Part(text="Our company policy strictly requires 100% Vegan Catering for all events.")])

    await memory_service.add_memory(app_name="GreenEventApp", user_id=user_id, content=memory_event)
