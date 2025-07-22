# analysis_agent.py
import logging

from crewai import Agent, Task, Crew

from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser

from base_agent import BaseJiraAgent
from ..models.requirement_review import RequirementReview


class AnalysisAgent(BaseJiraAgent):
    def __init__(self, config, jira_client, vector_manager=None):
        super().__init__(config, jira_client, vector_manager)
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        # Create a new CrewAI agent for analysis tasks
        return Agent(
            role="Requirement Reviewer",
            goal="Evaluate the quality of 'Draft Requirement' JIRA tickets for readiness to be implemented as code",
            backstory=(
                "You are a senior software analyst responsible for quality-gating incoming requirements. "
                "Your task is to determine whether a 'Draft Requirement' JIRA ticket contains the necessary information "
                "for it to be implemented by a developer without further clarification. "
                "You must evaluate each ticket against a fixed set of quality checks. "
                "You can use an embedding of the codebase embedding that you have been provided with."
                "If the requirement passes all critical checks, it should be marked as 'Accepted'. Otherwise, mark it as 'Rejected'.\n\n"
                "Begin the output by providing a synopsis of the specified requirement using common sense language."
                "Do not attempt to provide a synopsis if the sense of the requirement cannot be ascertained.\n"
                "Again, do not hallucinate a synopsis if the sense of the requirement cannot be ascertained.\n\n"

                "For the output\n"

                "Begin with a header called 'Review Summary'\n"
                "Then, create a review table with one row per ticket and three columns per row:\n"
                "CHECK | RESULT | REASON\n\n"

                "Always perform these checks in order:\n"
                "1. Title clarity – Is the title specific, relevant, and informative?\n"
                "2. Project specified – Does the ticket clearly specify which project the requirement applies to?\n"
                "3. Language specified – Does the ticket clearly specify the implementation language or framework?\n"
                "4. Functional description – Is the core functionality described clearly and unambiguously?\n"
                "5. Input/output defined – Are the inputs and outputs (or their types) explicitly stated?\n"
                "6. Edge cases and constraints – Are any boundary conditions, constraints, or failure modes described?\n"
                "7. Success criteria – Are there objective or testable conditions for completion?\n"
                "8. Scope feasibility – Can the task reasonably be completed by a single developer without additional context?\n\n"

                "For RESULT, use:\n"
                "✅ for pass\n"
                "❌ for fail\n\n"

                "For REASON:\n"
                "- If passed (✅), leave empty\n"
                "- If failed (❌), provide a brief, constructive explanation\n\n"

                "If any checks fail (❌), you must provide a complete rewritten version of the requirement that addresses all failed checks.\n"
                "The reformulation should:\n"
                "- Retain the original content and style, minus the deficiencies"
                "- Fix all identified deficiencies\n"
                "- Maintain the original intent of the requirement\n"
                "- Be clear, specific, and implementable\n"
                "- Include all necessary details that were missing\n\n"

                "After the review, use the appropriate tools to update statuses and/or communicate feedback.\n\n"
            ),
            output_parser=PydanticOutputParser(pydantic_object=RequirementReview),
            verbose=True,
            llm=ChatOpenAI(model="gpt-4", temperature=0.2) # Low-ish temperature for consistent reviewer feedback
        )

    def get_tools(self) -> list:
        # Define tools necessary for the analysis agent, such as semantic search and JIRA interaction tools
        tools = []
        # Add tools here as needed
        return tools

    def execute_task(self, task_description: str, **kwargs) -> dict:
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
            # Log the error and return a failure response
            logging.error(f"Error executing task: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': self.__class__.__name__
            }