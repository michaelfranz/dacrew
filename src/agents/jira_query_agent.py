"""JIRA Query Agent for searching and retrieving JIRA issues"""

import logging
from typing import List, Dict, Any, Optional
from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .base_agent import BaseJIRAAgent
from ..utils import build_jql_query, extract_issue_keys, validate_issue_key

logger = logging.getLogger(__name__)


class SearchIssuesTool(BaseTool):
    """Tool for searching JIRA issues"""
    name: str = "search_issues"
    description: str = "Search for JIRA issues using JQL or natural language query. Parameters: query (str), project (str, optional), max_results (int, default=10)"

    def _run(self, query: str, project: str = None, max_results: int = 10) -> str:
        """Search for JIRA issues"""
        # Access jira_client from the agent that created this tool
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: JIRA client not available"

        try:
            # Check if query is already JQL or needs to be built
            if any(keyword in query.lower() for keyword in ['and', 'or', 'order by', '=']):
                jql = query
            else:
                jql = build_jql_query(
                    project=project,
                    text_search=query
                )

            issues = jira_client.search_issues(jql, max_results)

            if not issues:
                return f"No issues found for query: {query}"

            # Format results
            result = f"Found {len(issues)} issue(s):\n\n"
            for issue in issues:
                result += f"• [{issue['key']}] {issue['summary']}\n"
                result += f"  Status: {issue['status']} | Assignee: {issue['assignee']}\n"
                result += f"  URL: {issue['url']}\n\n"

            return result

        except Exception as e:
            logger.error(f"Error searching issues: {e}")
            return f"Error searching issues: {str(e)}"


class GetIssueDetailsTool(BaseTool):
    """Tool for getting detailed information about a specific issue"""
    name: str = "get_issue_details"
    description: str = "Get detailed information about a specific JIRA issue. Parameters: issue_key (str)"

    def _run(self, issue_key: str) -> str:
        """Get detailed information about a specific issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: JIRA client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"Invalid issue key format: {issue_key}"

            issue = jira_client.get_issue(issue_key)

            if not issue:
                return f"Issue {issue_key} not found"

            # Format detailed information
            result = f"ISSUE DETAILS: {issue['key']}\n"
            result += f"{'=' * 50}\n"
            result += f"Summary: {issue['summary']}\n"
            result += f"Status: {issue['status']}\n"
            result += f"Priority: {issue['priority']}\n"
            result += f"Type: {issue['issue_type']}\n"
            result += f"Project: {issue['project']}\n"
            result += f"Assignee: {issue['assignee']}\n"
            result += f"Reporter: {issue['reporter']}\n"
            result += f"Created: {issue['created']}\n"
            result += f"Updated: {issue['updated']}\n"
            result += f"URL: {issue['url']}\n\n"

            if issue['description']:
                result += f"Description:\n{issue['description']}\n\n"

            if issue['labels']:
                result += f"Labels: {', '.join(issue['labels'])}\n"

            if issue['components']:
                result += f"Components: {', '.join(issue['components'])}\n"

            return result

        except Exception as e:
            logger.error(f"Error getting issue details: {e}")
            return f"Error getting issue details: {str(e)}"


class GetProjectInfoTool(BaseTool):
    """Tool for getting project information"""
    name: str = "get_project_info"
    description: str = "Get information about available JIRA projects. No parameters required."

    def _run(self) -> str:
        """Get information about available projects"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: JIRA client not available"

        try:
            projects = jira_client.get_projects()

            if not projects:
                return "No projects found or accessible"

            result = f"Available Projects ({len(projects)}):\n\n"
            for project in projects:
                result += f"• {project['key']} - {project['name']}\n"
                if project['description']:
                    result += f"  Description: {project['description'][:100]}...\n"
                result += "\n"

            return result

        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return f"Error getting project info: {str(e)}"


class JIRAQueryAgent(BaseJIRAAgent):
    """Agent specialized in querying and retrieving JIRA issues"""

    def _create_agent(self) -> Agent:
        """Create the JIRA Query Agent"""
        return Agent(
            role="JIRA Query Specialist",
            goal="Search, retrieve, and analyze JIRA issues based on user queries",
            backstory="""You are an expert in JIRA Query Language (JQL) and JIRA issue management. 
            You help users find the exact issues they're looking for by translating their natural 
            language requests into precise JQL queries and retrieving detailed issue information.""",
            tools=self.get_tools(),
            llm=self.llm,
            verbose=True
        )

    def get_tools(self) -> List[BaseTool]:
        """Get tools for the JIRA Query Agent"""
        tools = [
            SearchIssuesTool(),
            GetIssueDetailsTool(),
            GetProjectInfoTool()
        ]

        # Inject jira_client into each tool
        for tool in tools:
            setattr(tool, '_jira_client', self.jira_client)

        return tools