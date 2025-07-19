"""Enhanced JIRA client with AI-friendly methods"""

import logging
import json
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

    def get_create_meta(self, project_key: str, issue_type: str) -> Dict[str, Any]:
        """Get create metadata for a specific project and issue type"""
        try:
            # Get creation metadata to understand what fields are available
            meta = self._client.createmeta(
                projectKeys=project_key,
                issuetypeNames=issue_type,
                expand='projects.issuetypes.fields'
            )
            
            if meta['projects']:
                project = meta['projects'][0]
                if project['issuetypes']:
                    return project['issuetypes'][0]['fields']
            return {}
        except Exception as e:
            logger.error(f"Failed to get create metadata: {e}")
            return {}

    def _parse_jira_error(self, error: JIRAError) -> str:
        """Parse JIRA error response and provide helpful error messages"""
        try:
            # Try to extract the response text for detailed error info
            if hasattr(error, 'response') and error.response:
                try:
                    error_data = json.loads(error.response.text)
                    
                    # Handle error messages
                    if 'errorMessages' in error_data and error_data['errorMessages']:
                        return "; ".join(error_data['errorMessages'])
                    
                    # Handle field-specific errors
                    if 'errors' in error_data and error_data['errors']:
                        error_details = []
                        for field, message in error_data['errors'].items():
                            if 'cannot be set' in message:
                                error_details.append(f"Field '{field}' is not available for this issue type/project")
                            elif 'unknown' in message.lower():
                                error_details.append(f"Field '{field}': {message}")
                            else:
                                error_details.append(f"{field}: {message}")
                        
                        if error_details:
                            return "; ".join(error_details)
                
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            return str(error)
            
        except Exception:
            return str(error)

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
            # Validate issue type for the project
            valid_issue_types = self.get_issue_types(project_key)
            valid_type_names = [it['name'] for it in valid_issue_types]
            
            if issue_type not in valid_type_names:
                raise ValueError(
                    f"Invalid issue type '{issue_type}' for project '{project_key}'. "
                    f"Valid types: {', '.join(valid_type_names)}"
                )

            # Get available fields for this issue type to avoid field errors
            available_fields = self.get_create_meta(project_key, issue_type)

            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type}
            }

            # Only add fields that are actually available for this issue type
            for field_key, field_value in kwargs.items():
                if field_key in available_fields:
                    issue_dict[field_key] = field_value
                else:
                    logger.warning(f"Field '{field_key}' not available for issue type '{issue_type}' in project '{project_key}', skipping")

            new_issue = self._client.create_issue(fields=issue_dict)
            logger.info(f"Created issue: {new_issue.key}")
            return self._format_issue(new_issue)
            
        except ValueError as e:
            # Re-raise validation errors as-is
            logger.error(f"Validation error creating issue: {e}")
            raise
        except JIRAError as e:
            logger.error(f"Failed to create issue: {e}")
            
            # Parse the error for better user feedback
            parsed_error = self._parse_jira_error(e)
            
            # Provide helpful suggestions based on error type
            suggestions = []
            
            if "issue type" in parsed_error.lower():
                valid_issue_types = self.get_issue_types(project_key)
                valid_type_names = [it['name'] for it in valid_issue_types]
                suggestions.append(f"Valid issue types for project '{project_key}': {', '.join(valid_type_names)}")
            
            if "priority" in parsed_error.lower():
                if "cannot be set" in parsed_error.lower():
                    suggestions.append(f"Priority field is not available for issue type '{issue_type}' in project '{project_key}'")
                    suggestions.append("Try creating the issue without the --priority flag, or use a different issue type")
                else:
                    priorities = self.get_priorities()
                    valid_priorities = [p['name'] for p in priorities]
                    suggestions.append(f"Valid priorities: {', '.join(valid_priorities)}")
            
            if "assignee" in parsed_error.lower():
                if "cannot be set" in parsed_error.lower():
                    suggestions.append(f"Assignee field is not available for issue type '{issue_type}' in project '{project_key}'")
                    suggestions.append("Try creating the issue without the --assignee flag")
            
            # Create comprehensive error message
            error_message = f"JIRA Error: {parsed_error}"
            if suggestions:
                error_message += f"\n\nSuggestions:\n• " + "\n• ".join(suggestions)
            
            raise JIRAError(error_message)
            
        except Exception as e:
            logger.error(f"Unexpected error creating issue: {e}")
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