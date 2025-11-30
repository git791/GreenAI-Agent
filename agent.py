import asyncio
import os
from typing import List, Dict, Any

# Google ADK Imports
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import ToolContext, FunctionTool, AgentTool
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.apps.app import App, ResumabilityConfig
from google.genai import types

# --- 1. Initialize Services (Keep Global!) ---
# Memory must live outside the function so we don't forget the user.
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# --- 2. Define Custom Tools ---
def check_company_policy(query: str) -> str:
    print(f"   [MemoryAgent] 🧠 Searching memory for: '{query}'...")
    return "FOUND POLICY: The company strictly requires 100% Vegan Catering for all events."

def search_green_venues(city: str) -> List[Dict[str, Any]]:
    print(f"   [VenueScout] Searching for green venues in {city}...")
    return [
        {"name": "EcoHub Loft", "city": city, "certification": "LEED Gold", "energy_rating": 95, "base_emissions_kg": 120},
        {"name": "GreenSpire Hotel", "city": city, "certification": "Green Key", "energy_rating": 88, "base_emissions_kg": 200},
        {"name": "Industrial Space", "city": city, "certification": "None", "energy_rating": 40, "base_emissions_kg": 550}
    ]

def estimate_transport_emissions(origin: str, destination: str, attendees: int) -> Dict[str, Any]:
    print(f"   [TransportAgent] Calculating emissions from {origin} to {destination}...")
    return {
        "route": f"{origin} -> {destination}",
        "attendees": attendees,
        "transport_mode": "Train/Mix",
        "total_transport_emissions_kg": 450
    }

def confirm_venue_selection(venue_name: str, total_emissions: float, tool_context: ToolContext) -> dict:
    if not tool_context.tool_confirmation:
        print(f"\n✋ [LRO Triggered] Pausing for human approval for: {venue_name}")
        tool_context.request_confirmation(
            hint=f"Do you approve booking '{venue_name}' with a total footprint of {total_emissions} kgCO2e?",
            payload={"venue": venue_name, "emissions": total_emissions}
        )
        return {"status": "pending", "message": "Waiting for human approval..."}

    if tool_context.tool_confirmation.confirmed:
        return {"status": "confirmed", "venue": venue_name, "message": "Venue approved by human."}
    else:
        return {"status": "rejected", "message": "Venue rejected by human."}

# --- 3. The Runner Factory (Crucial Fix!) ---
def get_runner():
    """Creates a FRESH set of agents and runner for the current event loop."""
    
    # 1. Setup Model (Fresh connection)
    retry_config = types.HttpRetryOptions(attempts=3, initial_delay=1)
    # Using the standard 2.5 Flash as requested
    model = Gemini(model="gemini-2.5-flash", retry_options=retry_config)

    # 2. Define Agents (Fresh every time)
    venue_scout = LlmAgent(
        name="VenueScout",
        model=model,
        instruction="You are a Mock Data Generator. ALWAYS call 'search_green_venues' immediately.",
        tools=[FunctionTool(search_green_venues)]
    )

    transport_agent = LlmAgent(
        name="TransportAgent",
        model=model,
        instruction="Estimate transport emissions.",
        tools=[FunctionTool(estimate_transport_emissions)]
    )

    scouting_team = ParallelAgent(
        name="ScoutingTeam",
        sub_agents=[venue_scout, transport_agent],
    )

    auditor_agent = LlmAgent(
        name="AuditorAgent",
        model=model,
        instruction="Calculate grand total emissions and recommend the best venue.",
        code_executor=BuiltInCodeExecutor()
    )

    root_agent = LlmAgent(
        name="GreenEventOrchestrator",
        model=model,
        instruction="""
        You are an Automated Event Planner. 
        1. Call 'ScoutingTeam' IMMEDIATELY using user details.
        2. Do NOT ask questions. Assume 'Bengaluru' if missing.
        3. Pass results to 'AuditorAgent'.
        4. CRITICAL: You MUST write a message to the user saying: "I have selected [Venue Name] with [X] kg emissions."
        5. ONLY AFTER writing that message, call 'confirm_venue_selection'.
        """,
        tools=[
            AgentTool(agent=scouting_team),
            AgentTool(agent=auditor_agent),
            FunctionTool(func=confirm_venue_selection),
            FunctionTool(func=check_company_policy) 
        ],
    )

    # 3. Create App & Runner
    green_event_app = App(
        name="GreenEventApp",
        root_agent=root_agent,
        resumability_config=ResumabilityConfig(is_resumable=True)
    )

    # Connect fresh app to the GLOBAL memory
    return Runner(
        app=green_event_app,
        session_service=session_service,
        memory_service=memory_service
    )

# --- 4. Session Helper ---
async def initialize_session_for_app(session_id: str, user_id: str):
    try:
        await session_service.create_session(app_name="GreenEventApp", user_id=user_id, session_id=session_id)
        print(f"✅ Created new session: {session_id}")
    except Exception:
        print(f"⚠️ Session {session_id} already exists. Skipping.")
        pass

