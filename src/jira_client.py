"""JIRA client for handling JIRA API operations"""

import logging
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira.exceptions import JIRAError

from .config import Config

logger = logging.getLogger(__name__)


class JIRAClient:
    """Enhanced JIRA client with AI-friendly methods"""

    def __init__(self, config: Config):
        self.config = config
        self._client = None
        self._connect()

    def _connect(self):
        """Establish connection to JIRA"""
        try:
            self._client = JIRA(
                server=self.config.jira.url,
                basic_auth=(self.config.jira.username, self.config.jira.api_token)
            )
            logger.info("Successfully connected to JIRA")
        except JIRAError as e:
            logger.error(f"Failed to connect to JIRA: {e}")
            raise

    def test_connection(self) -> bool:
        """Test if JIRA connection is working"""
        try:
            user = self._client.myself()
            logger.info(f"Connection test successful for user: {user['displayName']}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all accessible projects"""
        try:
            projects = self._client.projects()
            return [
                {
                    'key': project.key,
                    'name': project.name,
                    'id': project.id,
                    'description': getattr(project, 'description', '')
                }
                for project in projects
            ]
        except JIRAError as e:
            logger.error(f"Failed to get projects: {e}")
            return []

    def get_issue_types(self, project_key: str = None) -> List[Dict[str, Any]]:
        """Get issue types for a project or all available issue types"""
        try:
            if project_key:
                project = self._client.project(project_key)
                issue_types = project.issueTypes
            else:
                # Get all issue types
                issue_types = self._client.issue_types()

            return [
                {
                    'id': issue_type.id,
                    'name': issue_type.name,
                    'description': getattr(issue_type, 'description', ''),
                    'subtask': getattr(issue_type, 'subtask', False)
                }
                for issue_type in issue_types
            ]
        except JIRAError as e:
            logger.error(f"Failed to get issue types: {e}")
            return []

    def get_priorities(self) -> List[Dict[str, Any]]:
        """Get available priorities"""
        try:
            priorities = self._client.priorities()
            return [
                {
                    'id': p.id,
                    'name': p.name,
                    'description': getattr(p, 'description', '')
                }
                for p in priorities
            ]
        except JIRAError as e:
            logger.error(f"Failed to get priorities: {e}")
            return []

    def get_statuses(self) -> List[Dict[str, Any]]:
        """Get available statuses"""
        try:
            statuses = self._client.statuses()
            return [
                {
                    'id': s.id,
                    'name': s.name,
                    'description': getattr(s, 'description', '')
                }
                for s in statuses
            ]
        except JIRAError as e:
            logger.error(f"Failed to get statuses: {e}")
            return []

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for issues using JQL"""
        try:
            issues = self._client.search_issues(jql, maxResults=max_results)
            return [self._format_issue(issue) for issue in issues]
        except JIRAError as e:
            logger.error(f"Failed to search issues with JQL '{jql}': {e}")
            return []

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific issue by key"""
        try:
            issue = self._client.issue(issue_key)
            return self._format_issue(issue)
        except JIRAError as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return None

    def create_issue(self, project_key: str, summary: str, description: str,
                     issue_type: str = "Task", **kwargs) -> Optional[Dict[str, Any]]:
        """Create a new issue"""
        try:
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type}
            }

            # Add any additional fields
            issue_dict.update(kwargs)

            new_issue = self._client.create_issue(fields=issue_dict)
            logger.info(f"Created issue: {new_issue.key}")
            return self._format_issue(new_issue)
        except JIRAError as e:
            logger.error(f"Failed to create issue: {e}")
            return None

    def update_issue(self, issue_key: str, **fields) -> bool:
        """Update an existing issue"""
        try:
            issue = self._client.issue(issue_key)
            issue.update(fields=fields)
            logger.info(f"Updated issue: {issue_key}")
            return True
        except JIRAError as e:
            logger.error(f"Failed to update issue {issue_key}: {e}")
            return False

    def add_comment(self, issue_key: str, comment: str) -> bool:
        """Add a comment to an issue"""
        try:
            self._client.add_comment(issue_key, comment)
            logger.info(f"Added comment to issue: {issue_key}")
            return True
        except JIRAError as e:
            logger.error(f"Failed to add comment to {issue_key}: {e}")
            return False

    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all comments for an issue"""
        try:
            issue = self._client.issue(issue_key)
            return [
                {
                    'id': comment.id,
                    'author': comment.author.displayName,
                    'body': comment.body,
                    'created': comment.created,
                    'updated': comment.updated
                }
                for comment in issue.fields.comment.comments
            ]
        except JIRAError as e:
            logger.error(f"Failed to get comments for {issue_key}: {e}")
            return []

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get available transitions for an issue"""
        try:
            transitions = self._client.transitions(issue_key)
            return [
                {
                    'id': transition['id'],
                    'name': transition['name'],
                    'to': transition['to']['name']
                }
                for transition in transitions
            ]
        except JIRAError as e:
            logger.error(f"Failed to get transitions for {issue_key}: {e}")
            return []

    def transition_issue(self, issue_key: str, transition_id: str) -> bool:
        """Transition an issue to a new status"""
        try:
            self._client.transition_issue(issue_key, transition_id)
            logger.info(f"Transitioned issue {issue_key} with transition {transition_id}")
            return True
        except JIRAError as e:
            logger.error(f"Failed to transition issue {issue_key}: {e}")
            return False

    def _format_issue(self, issue) -> Dict[str, Any]:
        """Format JIRA issue object to dictionary"""
        return {
            'key': issue.key,
            'id': issue.id,
            'summary': issue.fields.summary,
            'description': getattr(issue.fields, 'description', ''),
            'status': issue.fields.status.name,
            'priority': getattr(issue.fields.priority, 'name', 'None') if issue.fields.priority else 'None',
            'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
            'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
            'created': issue.fields.created,
            'updated': issue.fields.updated,
            'project': issue.fields.project.key,
            'issue_type': issue.fields.issuetype.name,
            'labels': getattr(issue.fields, 'labels', []),
            'components': [comp.name for comp in getattr(issue.fields, 'components', [])],
            'fix_versions': [ver.name for ver in getattr(issue.fields, 'fixVersions', [])],
            'url': f"{self.config.jira.url}/browse/{issue.key}"
        }