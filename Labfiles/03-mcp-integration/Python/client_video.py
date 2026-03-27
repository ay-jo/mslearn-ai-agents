import os
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import McpTool, ToolSet

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Connect to the agents client
agent_client = AgentsClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential
            (exclude_environment_credential=True,
            exclude_managed_identity_credential=True)
)

# MCP server configuration
mcp_server_url = "https://learn.microsoft.com/api/mcp"
mcp_server_label = "mslearn"

# Initialize agent MCP tool
mcp_tool = McpTool(
    server_label=mcp_server_label,
    server_url=mcp_server_url,
)

mcp_tool.set_approval_mode("never")

toolset = ToolSet()
toolset.add(mcp_tool)

# Create agent with MCP tool and process agent run
with agents_client:

    # Create a new agent
    agent = agents_client.create_agent(
        model=model_deployment,
        name="my-mcp-agent",
        instructions="""
        You have access to a MCP server called `microsoft.docs.mcp` - this tool allows you to search through Microsoft's latest official documentation.  Use the available MCP tools to answer questions and perform tasks."""
    )

    # Log info
    print(f"Created agent, ID: {agent.id}")
    print(f"MCP Server: {mcp_tool.server_label} at {mcp_tool.server_url}")

    # Create thread for communication
    thread = agents_client.threads.create()
    print(f"Created thread, ID: {thread.id}")

    # Create a message on the thread
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content="Give me the Azure CLI commands to create an Azure Container App with a managed identity"
    )
    print(f"Created message, ID: {message.id}")

    # Create and process agent run in thread with MCP tools
    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id, toolset=toolset)
    print(f"Created run, ID: {run.id}")

    # Check run status
    print(f"Run completed with status: {run.status}")
    if run.status == "failed":
    print(f"Run failed: {run.last_error}")

    # Display run steps and tool calls
    run_steps = agents_client.run_steps.list(thread_id=thread.id, run_id=run.id)
    for step in run_steps:
        print(f"Step {step['id']} status: {step['status']}")

        # Check if ther are tool calls in the step details
        step_details = step.get("step_details", {})
        tool_calls = step_details.get("tool_calls", {})

        if tool_calls:
            # Display the MCP tool call details
            print(" MCP Tool calls:")
            for call in tool_calls:
                print(f"    Tool Call ID: {call.get('id')}")
