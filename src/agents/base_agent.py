"""Base agent class for Dacrew"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

from ..config import Config
from ..jira_client import JiraClient

logger = logging.getLogger(__name__)


class BaseJiraAgent(ABC):
    """Base class for Jira AI agents"""

    def __init__(self, config: Config, jira_client: JiraClient, vector_manager=None):
        self.config = config
        self.jira_client = jira_client
        self.vector_manager = vector_manager
        self.llm = self._initialize_llm()
        self.agent = self._create_agent()

    def _initialize_llm(self):
        """Initialize the language model"""
        return ChatOpenAI(
            model=self.config.ai.model,
            temperature=self.config.ai.temperature,
            openai_api_key=self.config.ai.openai_api_key
        )

    @abstractmethod
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent - must be implemented by subclasses"""
        pass

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """Get tools for the agent - must be implemented by subclasses"""
        pass

    def execute_task(self, task_description: str, **kwargs) -> Dict[str, Any]:
        """Execute a task with this agent"""
        try:
            # CrewAI requires expected_output parameter
            task = Task(
                description=task_description,
                agent=self.agent,
                expected_output="A clear and comprehensive response to the user's query with relevant Jira issue information.",
                **kwargs
            )

            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=True
            )

            result = crew.kickoff()

            return {
                'success': True,
                'result': result,
                'agent': self.__class__.__name__
            }

        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': self.__class__.__name__
            }