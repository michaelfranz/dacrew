"""JIRA Query Agent for searching and retrieving JIRA issues"""

import logging
from typing import List, Dict, Any, Optional
from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .base_agent import BaseJIRAAgent
from ..utils import build_jql_query, parse_natural_language_query, validate_issue_key

logger = logging.getLogger(__name__)


class SearchIssuesInput(BaseModel):
    """Input schema for search_issues tool"""
    query: str = Field(..., description="JQL query or natural language search query")
    project: Optional[str] = Field(None, description="JIRA project key (optional)")
    max_results: int = Field(10, description="Maximum number of results to return")


class SearchIssuesTool(BaseTool):
    """Tool for searching JIRA issues"""
    name: str = "search_issues"
    description: str = "Search for JIRA issues using JQL or natural language query"
    args_schema: type[BaseModel] = SearchIssuesInput

    def _run(self, query: str, project: Optional[str] = None, max_results: int = 10) -> str:
        """Search for JIRA issues"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: JIRA client not available"

        try:
            # If query looks like JQL, use it directly
            if any(keyword in query.lower() for keyword in ['and', 'or', 'order by', '=', 'project']):
                jql = query
            else:
                # Parse natural language query
                params = parse_natural_language_query(query)
                if project:
                    params['project'] = project

                jql = build_jql_query(**params)

            logger.info(f"Searching with JQL: {jql}")
            issues = jira_client.search_issues(jql, max_results)

            if not issues:
                return "No issues found matching the query."

            # Format results
            result = f"Found {len(issues)} issue(s):\n\n"
            for issue in issues:
                result += f"**{issue['key']}** - {issue['summary']}\n"
                result += f"Status: {issue['status']} | Priority: {issue['priority']} | Assignee: {issue['assignee']}\n"
                result += f"URL: {issue['url']}\n\n"

            return result

        except Exception as e:
            logger.error(f"Error searching issues: {e}")
            return f"❌ Error searching issues: {str(e)}"


class GetIssueInput(BaseModel):
    """Input schema for get_issue tool"""
    issue_key: str = Field(..., description="JIRA issue key (e.g., 'PROJ-123')")


class GetIssueTool(BaseTool):
    """Tool for getting details of a specific JIRA issue"""
    name: str = "get_issue"
    description: str = "Get detailed information about a specific JIRA issue"
    args_schema: type[BaseModel] = GetIssueInput

    def _run(self, issue_key: str) -> str:
        """Get details of a specific JIRA issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: JIRA client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"❌ Invalid issue key format: {issue_key}"

            issue = jira_client.get_issue(issue_key)
            if not issue:
                return f"❌ Issue {issue_key} not found"

            # Format issue details
            result = f"**{issue['key']}** - {issue['summary']}\n\n"
            result += f"**Status:** {issue['status']}\n"
            result += f"**Priority:** {issue['priority']}\n"
            result += f"**Assignee:** {issue['assignee']}\n"
            result += f"**Reporter:** {issue['reporter']}\n"
            result += f"**Type:** {issue['issue_type']}\n"
            result += f"**Project:** {issue['project']}\n"
            result += f"**Created:** {issue['created']}\n"
            result += f"**Updated:** {issue['updated']}\n"
            result += f"**URL:** {issue['url']}\n"

            if issue['description']:
                result += f"\n**Description:**\n{issue['description']}\n"

            if issue['labels']:
                result += f"\n**Labels:** {', '.join(issue['labels'])}\n"

            return result

        except Exception as e:
            logger.error(f"Error getting issue: {e}")
            return f"❌ Error getting issue: {str(e)}"


class GetIssueCommentsInput(BaseModel):
    """Input schema for get_issue_comments tool"""
    issue_key: str = Field(..., description="JIRA issue key (e.g., 'PROJ-123')")


class GetIssueCommentsTool(BaseTool):
    """Tool for getting comments from a JIRA issue"""
    name: str = "get_issue_comments"
    description: str = "Get all comments from a JIRA issue"
    args_schema: type[BaseModel] = GetIssueCommentsInput

    def _run(self, issue_key: str) -> str:
        """Get comments from a JIRA issue"""
        jira_client = getattr(self, '_jira_client', None)
        if not jira_client:
            return "Error: JIRA client not available"

        try:
            if not validate_issue_key(issue_key):
                return f"❌ Invalid issue key format: {issue_key}"

            comments = jira_client.get_issue_comments(issue_key)

            if not comments:
                return f"No comments found for issue {issue_key}"

            result = f"Comments for {issue_key}:\n\n"
            for comment in comments:
                result += f"**{comment['author']}** ({comment['created']}):\n"
                result += f"{comment['body']}\n\n"

            return result

        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return f"❌ Error getting comments: {str(e)}"


class JIRAQueryAgent(BaseJIRAAgent):
    """Agent specialized in querying and retrieving JIRA issues"""

    def _create_agent(self) -> Agent:
        """Create the JIRA Query Agent"""
        return Agent(
            role="JIRA Query Specialist",
            goal="Search, retrieve, and analyze JIRA issues based on user queries",
            backstory="""You are an expert in JIRA query languages and data retrieval. 
            You help users find specific issues, analyze ticket patterns, and extract 
            meaningful insights from JIRA data using both JQL and natural language queries.""",
            tools=self.get_tools(),
            llm=self.llm,
            verbose=True
        )

    def get_tools(self) -> List[BaseTool]:
        """Get tools for the JIRA Query Agent"""
        tools = [
            SearchIssuesTool(),
            GetIssueTool(),
            GetIssueCommentsTool()
        ]

        # Inject jira_client into each tool
        for tool in tools:
            setattr(tool, '_jira_client', self.jira_client)

        return tools

    def search_issues(self, query: str, project: Optional[str] = None, max_results: int = 10) -> str:
        """Search for issues using natural language or JQL"""
        task_description = f"""
        Search for JIRA issues based on this query: "{query}"
        
        Guidelines:
        - If the query mentions "high priority", search for issues with priority = High
        - If the query mentions "assigned to me", use the current user context
        - If the query mentions specific status, filter by that status
        - If the query is already in JQL format, use it directly
        - Otherwise, build an appropriate JQL query
        
        Project context: {project or self.config.project.default_project_key}
        Max results: {max_results}
        
        Use the search_issues tool to find the issues and provide a clear summary.
        """

        result = self.execute_task(task_description)
        return result.get('result', 'No results found')