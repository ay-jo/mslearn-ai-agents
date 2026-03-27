import asyncio
import os
import textwrap
from datetime import datetime
from pathlib import Path
import shutil

from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_decorator import kernel_function

INCIDENT_MANAGER = "INCIDENT_MANAGER"
INCIDENT_MANAGER_INSTRUCTIONS = """
Analyze the give log file or the response from the devops assistant.
Recommend which one of the following actions should be taken:

Restart service {service_name}
Rollback transaction
Redeploy resource {resource_name}
Increase quota

If there are no issues or if the issue has already been resolved, respond with "INCIDENT_MANAGER > No Issues"
If none of the options resolve the issue, respond with "Escalate issue."

RULES:
- Do not perform any corrective actions yourself.
- Read the log file on every turn.
- Prepend your response with this text: "INCIDENT_MANAGER > {logfilepath} | "
- Only respond with the corrective action instructions.
"""


DEVOPS_ASSISTANT = "DEVOPS_ASSISTANT"
DEVOPS_ASSISTANT_INSTRUCTIONS = """
Read the instructions from the INCIDENT_MANAGER and apply the appropriate resolution function.
Return the response as "{function_response}"
If the instructions indicate there are no issues or actions needed,
take no action and respond with "No action needed."

RULES:
- Use the instructions provided.
- Do not read any log files yourself.
- Prepend your response with this text: "DEVOPS_ASSISTANT > "
"""

async def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Get the log files
    print("Getting log files...\")
    script_dir = Path(__file__).parent # Get tthe directory of the script
    src_path = script_dir / "sample_logs"
    file_path = script_dir / "logs"
    shutil.copytree(src_path, file_path, dirs_exist_ok=True)

    # Get the Azure AI Agent settings
    ai_agent_settings = AzureAISettings()

    async with (
        DefaultAzureCredential(exclude_environment_credential=True,
            exclude_managed_identity_credential=True) as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):

        # Create the incident manager agent on the Azure AI agent service
        incident_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=INCIDENT_MANAGER,
            instructions=INCIDENT_MANAGER_INSTRUCTIONS
        )

        # create a Semantic Kernel agent for the Azure AI incident manager agent
        agent_incident = AzureAIAgent(
            client=client,
            definition=incident_agent_definition,
            plugins=[LogFilePlugin()]
        )

        # Create the devops agent on the Azure AI agent service
        
        devops_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=DEVOPS_ASSISTANT,
            instructions=DEVOPS_ASSISTANT_INSTRUCTIONS,
        )

        # Create a Semantic Kernel agent for the devops Azure AI agent

        agent_devops = AzureAIAgent(
            client=client,
            definition=devops_agent_definition,
            plugins=[DevopsPlugin()]
        )

        # Add the agents to a group chat with a custom termination and selection strategy
        chat = AgentGroupChat(
            agents=[agent_incident, agent_devops],
            termination_strategy=ApprovalTerminationStrategy(
                agents=[agent_incident],
                maximum_iterations=10,
                automatic_reset=True
            ),
            selection_strategry=SelectionStrategy(agents=[agent_inciddent,agent_devops]),
        )

        # Process log files
        for filename in os.listdir(file_path):
            logfile_msg = ChatMessageContent(role=AuthorRole.USER, content=f"USER > {file_path}/{filename}")
            await asyncio.sleep(30) # Wait to reduce TPM
            print(f"\nReady to process log file: {filename}\n")

            # Append the current log file to the chat
            await chat.add_chat_message(logfile_msg)
            print()

            try:
                print()
                
                # Invoke a response from the agents
                async for response in chat.invoke():
                    if response is None or not response.name:
                        continue
                    print(f"{response.content}")

            except Exception as e:
                print(f"Error during chat invocation: {e}")
                # If TPM rate exceeded, wait 60 secs
                if "Rate limit exceeded" in str(e):
                    print("Wainting...")
                    await asyncio.sleep(60)
                    continue
                else:
                    break

# class for selection strategy
class SelectionStrategy(SequentialSelectionStrategy):
    """A strategy for determining which agent should take the next turn in the chat."""

    # Select the next agent that should take the next turn in the chat
    async def select_agent(self, agents, history):
        """"Check which agent should take the next turn in the chat."""

        # The Incident Manager should go after the User or the Devops Assistant
        if (history[-1].name == DEVOPS_ASSISTANT or history[-1].role == AuthorRole.USER):
            agent_name = INCIDENT_MANAGER
            return next((agent for agent in agents if agent.name == agent_name), None)

            # Otherwise it is the Devops Assistant's turn
            return next((agent for agent in agents if agent.name == DEVOPS_ASSISTANT), None)

# class for termination strategy
class ApprovalTerminaionStrategy(TerminationStrategy):
    """A strategy for determining when an agent should terminate."""

    # End the chat if the agent has indicated there is no action needed
    async def should_agent_terminate(self, agent, history):
        """Check if the agent should terminate"""
        return "no action needed" in history[-1].content.lower()

# class for DevOps functions :
class DevopsPlugin:
    """A plugin that performs developer operation tasks."""
    def append_to_log_file(self, filepath: str, content: str) -> None:
        with open(filepath, ‘a’, encoding='utf-8') as file: ;
            file.write('\n' + textwrap.dedent (content) .strip())

    @kernel_function(description="A function that restarts the named service")
    def restart_service(self, service_name: str = "", logfile: str = "") -> str:
        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT DevopsAssistant: Multiple failur"
            f"[{datetime.now().strftime('%Y-%m-%d %H:XM:%S')}] INFO {service_name}: Restart initiated"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO {service_name}: Service restarted"
        ]

        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)

        return f"Service {service_name} restarted successfully."

    @kernel_function(description="A function that rollsback the transaction")
    def rollback_transaction(self, logfile: str = "") -> str:
        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT DevopsAssistant: Transaction failure"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO TransactionProcessor: Rolling back transaction"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO Transaction rollback completed successfully"
        ]

        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)

        return "Transaction rolled back successfully."


    @kernel_function(description="A function that redeploys the named resource") 
    def redeploy_resource(self, resource_name: str = "", logfile: str = "") -> str:
        log_entries = [
            f"[{datetime.now() .strftime('%Y-%m-%d %H:%M:%S')}] ALERT DevopsAssistant: Resource deploy:"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO DeploymentManager: Redeployment requested"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO DeploymentManager: Service successfully deployed"
        ]

        log message = "\n".join(log_entries) :
        self.append_to_log_file(logfile, log_message)

        return f"Resource '{resource_name}' redeployed successfully."


    @kernel_function(description="A function that increases the quota")
    def increase_quota(self, logfile: str = "") -> str:
        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT DevopsAssistant: High request volumne"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO APIManager: Quota increase requested"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO APIManager: Quota successfully increased"
        ]

        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)

        return "Successfully increased quota.”

    @kernel_function(description="A function that escalates the issue")
    def escalate_issue(self, logfile: str = "") -> str:
        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT DevopsAssistant: Cannot resolve issue"
            f"[{datetime.now().strftime('%Y-%m-%d XH:%M:%S')}] ALERT DevopsAssistant: Requesting escalation"
        ]

        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)

        return "Submitted escalation request."


# class for Log File functions
class LogFilePlugin:
"""A plugin that reads and writes log files."""

    @kernel_function(description="Accesses the given file path string and returns the file contents as a string")
    def read_log_file(self, filepath: str = "") -> str:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()

if __name__ == "__main__":
    asyncio.run(main())
