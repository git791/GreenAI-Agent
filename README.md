# 🌱 GreenEvent AI: The Sustainable Event Orchestrator

> **Capstone Project for the Google AI Agents Intensive (2025)**
> **Track:** Agents for Good

## 1. The Problem: "Greenwashing" vs. Action
Corporate event planning is a logistical nightmare that generates massive carbon footprints. While many companies mandate "sustainability," enforcing it is manual and error-prone. Planners struggle to find verified LEED-certified venues, manually calculate attendee transport emissions, and often skip compliance checks due to time pressure. The result? "Green events" that are green in name only.

## 2. The Solution
**GreenEvent AI** is an autonomous orchestration agent that enforces sustainability. It integrates venue discovery, emission calculations, and corporate policy compliance into a single automated workflow.

Unlike standard LLMs that hallucinate data, GreenEvent AI uses **deterministic tools** to fetch venue certifications and perform math-heavy carbon emission calculations. Crucially, it solves the "AI Trust" problem by introducing a **Human-in-the-Loop (HITL)** approval step before any booking is finalized.

## 3. Prototype Note: Mock Data
To ensure this agent is fully testable by judges and stable for the demo, I have implemented **simulated data layers** (Mock Data) for the venue database and emission APIs.
* **Why?** This ensures the agent behaves deterministically during the evaluation without requiring external API keys for third-party carbon databases.
* **How?** The `VenueScout` and `TransportAgent` call Python functions that return realistic, structured JSON data, simulating exactly how a production API would behave.

## 4. Technical Architecture & Key Concepts
I built this agent using the **Google Agent Development Kit (ADK)**, directly applying specific patterns from the **5-Day Intensive curriculum**:

### 🏗️ A. Multi-Agent Systems & Parallelization (Ref: Day 1b & Day 5a)
Moving beyond the single-agent pattern, I implemented a `ParallelAgent` architecture ("ScoutingTeam") as explored in **Day 1b (Agent Architectures)**:
* **VenueScout Agent:** Searches for venues and filters by LEED/Green Key certifications.
* **TransportAgent:** *Simultaneously* calculates transport emissions.
This reduces latency and uses the **Agent-to-Agent** communication patterns from **Day 5a**.

### 🛑 B. Long-Running Operations (Ref: Day 2b)
To handle the risky booking process, I applied the **Tool Best Practices (Day 2b)** by implementing a **Long-Running Operation (LRO)**.
* When a venue is selected, the agent triggers a `tool_confirmation` request.
* The execution **pauses** (waiting for the Streamlit UI response).
* This ensures the agent never takes "action" without human authorization, the key safety pattern from the **Day 2b** module.

### 🧠 C. Sessions & Memory (Ref: Day 3a & 3b)
To bridge the gap between a stateless web interface (Streamlit) and a stateful agent, I implemented:
* **Session Management (Day 3a):** Using `InMemorySessionService` to maintain the conversation thread.
* **Context Preservation (Day 3b):** Ensuring the agent "remembers" event details (City, Date) even after the execution is paused/resumed for human approval.

## 5. The Journey: Challenges & Learnings
Moving from the course notebooks to a production-style IDE environment presented significant challenges:

* **IDE vs. Notebooks:** Transitioning code from a guided Notebook environment to a local IDE (VS Code) required handling dependencies, imports, and strict indentation rules that are often hidden in cell-based workflows.
* **Strict ADK Rules:** I struggled initially with the ADK's strict naming conventions (e.g., Root Agent naming) and wrapping functions into `FunctionTool` interfaces correctly. Debugging these structure errors was a major learning curve.
* **Prompt Engineering:** The agent initially behaved arrogantly, assuming it knew the best venue without checking. I had to iteratively refine the system instructions to ensure it remained helpful and strictly followed the "ask before booking" protocol.
* **API Management:** Managing the API keys and hitting rate limits with the LLM required implementing retry logic and careful session handling to avoid wasting quota on loop errors.
* **Deployment Strategy Pivot:** I initially containerized the application for **Google Cloud Run** (as covered in Day 5b). However, due to cloud billing constraints, I pivoted to **Streamlit Community Cloud** for the final hosting. This taught me how to adapt `Dockerfile` configurations to different hosting environments while keeping the core container logic intact.

---

## 🛠️ Setup & Installation

To run this agent locally:

### 1. Clone the Repository
```bash
git clone https://github.com/git791/GreenAI-Agent.git
cd GreenAI-Agent
```

### 2. Install Dependencies
Make sure you have Python 3.10+ installed.

```Bash
pip install -r requirements.txt
```

### 3. Set up Environment Variables
Create a `.env` file in the root directory and add your Google Gemini API key:
```Bash
GOOGLE_API_KEY=your_api_key_here
```

### 4. Run the App
Launch the Streamlit interface:
```Bash
streamlit run app.py
```

## 📂 File Structure
* `agent.py`: Contains the ADK logic, agent definitions, and tools.
* `app.py`: The Streamlit frontend and session management.
* `requirements.txt`: Python dependencies.
* `Dockerfile`: Configuration for deployment.

## 👥 The Team
* **Mohammed Ayaan Adil Ahmed**

* **Bibi Sufiya Shariff**
