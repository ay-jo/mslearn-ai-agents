import os
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, FunctionTool, ToolSet, ListSortOrder, MessageRole


# Clear the console
os.system('cls' if os.name=='nt' else 'clear')

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Priority agent definition
priority_agent_name = "priority_agent"
priority_agent_instructions = """
Assess how urgent a ticket is based on its description.

Respond with one of the following levels:
- High: User-facing or blocking issues
- Medium: Time-sensitive but not breaking anything
- Low: Cosmetic or non-urgent tasks

Only output the urgency level and a very brief explanation.
"""

# Team agent definition
team_agent_name = "team_agent"
team_agent_instructions = """
Decide which team should own each ticket.

Choose from the following teams:
- Frontend
- Backend
- Infrastructure
- Marketing

Base your answer on the content of the ticket.  Respond with the team name and a very brief explanation.
"""

# Effor agent definition
effort_agent_name = "effort_agent"
effort_agent_instructions = """
Estimate how much work each ticket will require. 

Use the following scale:
- Small: Can be completed in a day
- Medium: 2-3 days of work
- Large: Multi-day or cross-team effort

Base your estimate on the complexity implied by the ticket.  Respond with the effort level and a brief explanation.
"""

# Instructions for the primary agent
triage_agent_instructions = """
Triage the given ticket.  Use the connected tools to determine the ticket's priority,
which team it should be assigned to, and how much effort it may take.
"""

# Connect to the agents client

agent_client = AgentsClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential
            (exclude_environment_credential=True,
            exclude_managed_identity_credential=True)
)

with agents_client:

    # Create an agent to prioritize support tickets
    priority_agent = agent_client.create_agent(
            model=model_deployment,
            name=priority_agent_name,
            instructions=priority_agent_instructions
    )

    # Create a connected agent tool for the priority agent
    priority_agent_tool = ConnectedAgentTool(
        id=priority_agent.id,
        name=priority_agent_name,
        description="Assess the priority of a ticket"
    )

    # Create an agent to assign tickets to the appropriate team

    team_agent = agent_client.create_agent(
            model=model_deployment,
            name=team_agent_name,
            instructions=team_agent_instructions
    )

    # Create a connected agent tool for the team agent
    team_agent_tool = ConnectedAgentTool(
        id=team_agent.id,
        name=team_agent_name,
        description="Determines which team should take the ticket."
    )

    # Create an agent to estimate effort for a support ticket

    effort_agent = agent_client.create_agent(
            model=model_deployment,
            name=effort_agent_name,
            instructions=effort_agent_instructions
    )

    # Create connected agent tools for the effort agents

    effort_agent_tool = ConnectedAgentTool(
        id=effort_agent.id,
        name=effort_agent_name,
        description="Determines the effort required to complete the ticket"
    )

    # Create connected agent tools for the support agents


    # Create a main agent to triage support ticket processing by using Connected Agent tools
    agent - agents_client.create_agent(
        model=model_deployment,
        name="triage-agent",
        instructions=triage_agent_instructions,
        tools=[
            priority_agent_tool.definitions[0],
            team_agent_tool.definitions[0],
            effort_agent_tool.definitions[0],
        ]
    )


    # Create thread for the chat session
    print("Creating agent thread.")

    # Create the ticket prompt
    prompt = "Users can't reset their password from the mobile app."

    # Send a prompt to the agent
    message = agents_client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=prompt,
    )

    # Create and process Agent run in thread with tools
    print("Processing agent thread.  Please wait.")
    run = agent_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

    if run.status == "failed":
    print(f"Run failed: {run.last_error}")

    # Fetch and log all messages
    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for message in messages:
        if message.text_messages:
            last_msg = message.text_messages[-1]
            print(f"{message.role}:\{last_msg.text.value}\")

    # Clean up
    # Delete the agent when done
    print("Cleaning up agents:")
    agents_client.delete_agent(agent.id)
    print("Deleted triage agent.")


    # Delete the connected agents when done
    agents_client.delete_agent(priority_agent.id)
    print("Deleted priority agent.")
    agents_client.delete_agent(team_agent.id)
    print("Deleted team agent.")


    # Use the agents to triage a support issue


