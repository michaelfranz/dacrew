import logging
from typing import Optional

from ..config import Config, CrewAgentConfig, CrewTaskConfig
from ..embedding.embedding_manager import EmbeddingManager
from ..jira_client import JiraClient
from ..tasks.task_runner import TaskRunner

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all DaCrew agents.
    Agents execute tasks defined in the Crew configuration.
    """

    def __init__(self, config: Config, agent_name: str):
        self.config = config
        self.agent_config = self._find_agent(agent_name)
        if not self.agent_config:
            raise ValueError(f"Agent '{agent_name}' not found in .dacrew.yml")

        self.jira = JiraClient(config.jira)
        self.embedding_manager = EmbeddingManager(config.project)
        self.task_runner = TaskRunner(self.config, self.agent_config)
        self.name = agent_name

    def _find_agent(self, agent_name: str) -> Optional[CrewAgentConfig]:
        if not self.config.crew:
            return None
        for agent in self.config.crew.agents:
            if agent.name == agent_name:
                return agent
        return None

    def run(self, issue_id: str):
        """
        Run the agent for the given JIRA issue.
        1. Update JIRA to 'in_progress' state for the agent.
        2. Execute tasks in order.
        3. Update JIRA to 'done' or 'failed'.
        """
        self._log(f"agent {self.name} running for issue {issue_id}...")

        try:
            self._set_jira_status(issue_id, "in_progress")
            self._add_agent_comment(issue_id, "Started processing.")

            for task_name in self.agent_config.tasks:
                self._execute_task(issue_id, task_name)

            self._set_jira_status(issue_id, "done")
            self._add_agent_comment(issue_id, "Completed all tasks.")

        except Exception as e:
            logger.error(f"Agent {self.name} failed: {e}", exc_info=True)
            self._set_jira_status(issue_id, "failed")
            self._add_agent_comment(issue_id, "Failed: {str(e)}")

    def _execute_task(self, issue_id: str, task_name: str):
        """
        Execute a single task.
        """
        self._log(f"executing task '{task_name}' for issue {issue_id}.")
        task = self._find_task(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found in crew.tasks.")

        self.task_runner.run_task(task, issue_id)

    def _find_task(self, task_name: str) -> Optional[CrewTaskConfig]:
        if not self.config.crew:
            return None
        for task in self.config.crew.tasks:
            if task.name == task_name:
                return task
        return None

    def _set_jira_status(self, issue_id: str, stage: str):
        """
        Set the JIRA issue status based on the agent's jira_workflow mapping.
        """
        status = self.agent_config.jira_workflow.get(stage)
        if not status:
            self._log(f"No status mapping for stage '{stage}' in agent {self.name}.")
            return
        self.jira.transition_issue_by_status(issue_id, status)

    def _add_agent_comment(self, issue_key: str, comment: str) -> bool:
        tagged_comment = f"[Agent: {self.name}] {comment}"
        return self.jira.add_comment(issue_key, tagged_comment)

    def _log(self, message: str):
        logger.info(f"Agent {self.name} {message}")

        
