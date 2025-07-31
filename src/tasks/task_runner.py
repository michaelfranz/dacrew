import logging

from embedding import EmbeddingManager
from jira_client import JiraClient
from ..config import Config, CrewAgentConfig, CrewTaskConfig

logger = logging.getLogger(__name__)

from ..tools.tool_repository import resolve_tools

from crewai import Crew, Agent, Task, CrewOutput


class TaskRunner:
    def __init__(self, config: Config, agent_config: CrewAgentConfig):
        self.config = config
        self.agent_config = agent_config
        self.jira = JiraClient(config.jira)
        self.embedding_manager = EmbeddingManager(config.project)

    def run_task(self, task: CrewTaskConfig, issue_id: str):
        logger.info(f"[TaskRunner] Starting task {task.name} for issue {issue_id}.")

        # 1. Fetch JIRA issue details
        issue_data = self.jira.get_issue(issue_id)
        if not issue_data:
            raise ValueError(f"Issue {issue_id} not found in JIRA.")

        # 2. Build the Crew
        crew = self._build_crew(task, issue_data)

        # 3. Kick off Crew execution
        result = crew.kickoff()

        # 4. Handle the task result
        self._handle_task_output(task, issue_id, result)
        return result

    def _build_crew(self, task: CrewTaskConfig, issue_data: dict) -> Crew:
        """
        Build a CrewAI Crew object using the current agent and the given task.
        """
        # Create the Agent
        agent = Agent(
            role=self.agent_config.role,
            backstory=self.agent_config.backstory,
            goal=self.agent_config.goal,
            tools=resolve_tools(self.agent_config.tools),
            knowledge=resolve_knowledge(self.agent_config.knowledge),
            llm=self.agent_config.llm,
            verbose=True
        )

        # Create the Task
        task_obj = Task(
            description=f"{task.description}\n\nJIRA Issue: {issue_data['summary']}\n{issue_data['description']}",
            expected_output=task.output,
            agent=agent
        )

        return Crew(
            agents=[agent],
            tasks=[task_obj],
            verbose=True
        )

    def _handle_task_output(self, task: CrewTaskConfig, issue_id: str, result: CrewOutput):
        """
        Save or report the task's output (e.g., to JIRA).
        """
        comment = f"[Agent: {self.agent_config.name}] Completed task '{task.name}'. Output:\n{result}"
        self.jira.add_comment(issue_id, comment)