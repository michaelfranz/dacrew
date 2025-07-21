"""Jira Action Agent for creating, updating, and managing Jira issues"""

import logging
from typing import List

from crewai import Agent
from crewai.tools import BaseTool

from .base_agent import BaseJiraAgent
from ..utils import validate_issue_key

logger = logging.getLogger(__name__)


class CreateIssueTool(BaseTool):
    """Tool for creating new Jira issues"""
    name: str = "create_issue"
    description: str = "Create a new Jira issue. Parameters: project (str), summary (str), description (str), issue_type (str, default='Task'), priority (str, optional), assignee (str, optional)"

    def _run(self, project: str, summary: str, description: str,
             issue_type: str = "Task", priority: str = None, assignee: str = None) -> str:
        """Create a new Jira issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: Jira client not available"

        try:
            # Prepare additional fields
            kwargs = {}
            if priority:
                kwargs['priority'] = {'name': priority}
            if assignee:
                kwargs['assignee'] = {'name': assignee}

            issue = jira_client.create_issue(
                project_key=project,
                summary=summary,
                description=description,
                issue_type=issue_type,
                **kwargs
            )

            if issue:
                result = f"✅ Successfully created issue: {issue['key']}\n"
                result += f"Summary: {issue['summary']}\n"
                result += f"Status: {issue['status']}\n"
                result += f"URL: {issue['url']}\n"
                return result
            else:
                return "❌ Failed to create issue"

        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return f"❌ Error creating issue: {str(e)}"


class UpdateIssueTool(BaseTool):
    """Tool for updating existing Jira issues"""
    name: str = "update_issue"
    description: str = "Update an existing Jira issue. Parameters: issue_key (str), summary (str, optional), description (str, optional), assignee (str, optional), priority (str, optional)"

    def _run(self, issue_key: str, summary: str = None, description: str = None,
             assignee: str = None, priority: str = None) -> str:
        """Update an existing Jira issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: Jira client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"❌ Invalid issue key format: {issue_key}"

            # Build update fields
            fields = {}
            if summary:
                fields['summary'] = summary
            if description:
                fields['description'] = description
            if assignee:
                fields['assignee'] = {'name': assignee}
            if priority:
                fields['priority'] = {'name': priority}

            if not fields:
                return "❌ No fields to update specified"

            success = jira_client.update_issue(issue_key, **fields)

            if success:
                result = f"✅ Successfully updated issue: {issue_key}\n"
                result += f"Updated fields: {', '.join(fields.keys())}\n"
                return result
            else:
                return f"❌ Failed to update issue: {issue_key}"

        except Exception as e:
            logger.error(f"Error updating issue: {e}")
            return f"❌ Error updating issue: {str(e)}"


class AddCommentTool(BaseTool):
    """Tool for adding comments to Jira issues"""
    name: str = "add_comment"
    description: str = "Add a comment to a Jira issue. Parameters: issue_key (str), comment (str)"

    def _run(self, issue_key: str, comment: str) -> str:
        """Add a comment to a Jira issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: Jira client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"❌ Invalid issue key format: {issue_key}"

            success = jira_client.add_comment(issue_key, comment)

            if success:
                return f"✅ Successfully added comment to issue: {issue_key}"
            else:
                return f"❌ Failed to add comment to issue: {issue_key}"

        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return f"❌ Error adding comment: {str(e)}"


class TransitionIssueTool(BaseTool):
    """Tool for transitioning Jira issues"""
    name: str = "transition_issue"
    description: str = "Transition a Jira issue to a different status. Parameters: issue_key (str), status (str)"

    def _run(self, issue_key: str, status: str) -> str:
        """Transition a Jira issue to a different status"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: Jira client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"❌ Invalid issue key format: {issue_key}"

            # Get available transitions
            transitions = jira_client.get_transitions(issue_key)

            if not transitions:
                return f"❌ No transitions available for issue: {issue_key}"

            # Find matching transition
            target_transition = None
            for transition in transitions:
                if transition['to'].lower() == status.lower():
                    target_transition = transition
                    break

            if not target_transition:
                available = [t['to'] for t in transitions]
                return f"❌ Status '{status}' not available. Available: {', '.join(available)}"

            success = jira_client.transition_issue(issue_key, target_transition['id'])

            if success:
                return f"✅ Successfully transitioned {issue_key} to {status}"
            else:
                return f"❌ Failed to transition issue: {issue_key}"

        except Exception as e:
            logger.error(f"Error transitioning issue: {e}")
            return f"❌ Error transitioning issue: {str(e)}"


class GetTransitionsTool(BaseTool):
    """Tool for getting available transitions"""
    name: str = "get_transitions"
    description: str = "Get available transitions for a Jira issue. Parameters: issue_key (str)"

    def _run(self, issue_key: str) -> str:
        """Get available transitions for a Jira issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: Jira client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"❌ Invalid issue key format: {issue_key}"

            transitions = jira_client.get_transitions(issue_key)

            if not transitions:
                return f"No transitions available for issue: {issue_key}"

            result = f"Available transitions for {issue_key}:\n\n"
            for transition in transitions:
                result += f"• {transition['name']} → {transition['to']}\n"

            return result

        except Exception as e:
            logger.error(f"Error getting transitions: {e}")
            return f"❌ Error getting transitions: {str(e)}"


class JiraActionAgent(BaseJiraAgent):
    """Agent specialized in performing actions on Jira issues"""

    def _create_agent(self) -> Agent:
        """Create the Jira Action Agent"""
        return Agent(
            role="Jira Action Specialist",
            goal="Create, update, and manage Jira issues based on user requests",
            backstory="""You are an expert in Jira issue management and workflows. 
            You help users create new issues, update existing ones, manage transitions, 
            and perform other Jira administrative tasks efficiently and accurately.""",
            tools=self.get_tools(),
            llm=self.llm,
            verbose=True
        )

    def get_tools(self) -> List[BaseTool]:
        """Get tools for the Jira Action Agent"""
        tools = [
            CreateIssueTool(),
            UpdateIssueTool(),
            AddCommentTool(),
            TransitionIssueTool(),
            GetTransitionsTool()
        ]

        # Inject jira_client into each tool
        for tool in tools:
            setattr(tool, '_jira_client', self.jira_client)

        return tools