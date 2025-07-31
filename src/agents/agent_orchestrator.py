import logging
from typing import Optional

from agents import BaseAgent
from config import Config, CrewAgentConfig
from jira_client import JiraClient

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Determines which agent should be invoked based on Jira issue status
    and runs the appropriate agent.
    """

    def __init__(self, config: Config):
        self.config = config
        self.jira = JiraClient(config.jira)

    def run_for_issue(self, issue_id: str):
        issue = self.jira.get_issue(issue_id)
        if not issue:
            logger.warning(f"Issue {issue_id} not found.")
            return

        current_status = issue["status"]
        agent = self._find_agent_for_status(current_status)

        if not agent:
            logger.info(f"No agent mapped to status '{current_status}'.")
            return

        logger.info(f"Triggering agent {agent.name} for issue {issue_id}.")
        agent_instance = BaseAgent(self.config, agent.name)
        agent_instance.run(issue_id)

    def _find_agent_for_status(self, status_name: str) -> Optional[CrewAgentConfig]:
        if not self.config.crew:
            return None
        for agent in self.config.crew.agents:
            if status_name in agent.jira_workflow.values():
                return agent
        return None