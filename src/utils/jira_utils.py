"""Utility functions for Dacrew"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def validate_issue_key(key: str) -> bool:
    """Validate Jira issue key format"""
    pattern = r'^[A-Z][A-Z0-9]+-\d+$'
    return bool(re.match(pattern, key))


def extract_issue_keys(text: str) -> List[str]:
    """Extract Jira issue keys from text"""
    pattern = r'\b[A-Z][A-Z0-9]+-\d+\b'
    return re.findall(pattern, text)


def format_issue_summary(summary: str, max_length: int = 50) -> str:
    """Format issue summary for display"""
    if len(summary) <= max_length:
        return summary
    return summary[:max_length-3] + "..."


def get_common_statuses() -> List[str]:
    """Get common Jira statuses"""
    return [
        'Open', 'In Progress', 'Done', 'Closed', 'Resolved',
        'To Do', 'In Review', 'Testing', 'Blocked', 'Cancelled'
    ]


def get_common_priorities() -> List[str]:
    """Get common Jira priorities"""
    return [
        'Blocker', 'Critical', 'High', 'Major', 'Medium',
        'Normal', 'Low', 'Minor', 'Trivial'
    ]


def get_common_issue_types() -> List[str]:
    """Get common Jira issue types"""
    return [
        'Bug', 'Task', 'Story', 'Epic', 'Sub-task',
        'Improvement', 'New Feature', 'Defect', 'Issue'
    ]


def parse_relative_date(date_str: str) -> Optional[str]:
    """Parse relative date strings like 'last week', 'yesterday', etc."""
    date_str = date_str.lower().strip()
    now = datetime.now()

    if date_str in ['today']:
        return now.strftime('%Y-%m-%d')
    elif date_str in ['yesterday']:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    elif date_str in ['last week', 'past week']:
        return (now - timedelta(weeks=1)).strftime('%Y-%m-%d')
    elif date_str in ['last month', 'past month']:
        return (now - timedelta(days=30)).strftime('%Y-%m-%d')
    elif date_str.startswith('last ') and date_str.endswith(' days'):
        try:
            days = int(date_str.split()[1])
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            return None

    return None


def build_jql_query(
        project: str = None,
        assignee: str = None,
        status: str = None,
        priority: str = None,
        issue_type: str = None,
        text_search: str = None,
        labels: List[str] = None,
        **kwargs
) -> str:
    """Build JQL query from parameters"""
    conditions = []

    if project:
        conditions.append(f"project = {project}")

    if assignee:
        if assignee.lower() in ['me', 'currentuser', 'current user']:
            conditions.append("assignee = currentUser()")
        else:
            conditions.append(f"assignee = \"{assignee}\"")

    if status:
        conditions.append(f"status = \"{status}\"")

    if priority:
        # Map common priority names to what might exist in Jira
        priority_mapping = {
            'high': ['High', 'Major', 'Critical', 'Blocker'],
            'medium': ['Medium', 'Normal'],
            'low': ['Low', 'Minor', 'Trivial']
        }

        if priority.lower() in priority_mapping:
            mapped_priorities = priority_mapping[priority.lower()]
            priority_conditions = [f"priority = \"{p}\"" for p in mapped_priorities]
            conditions.append(f"({' OR '.join(priority_conditions)})")
        else:
            conditions.append(f"priority = \"{priority}\"")

    if issue_type:
        # Map common issue type names to what might exist in Jira
        issue_type_mapping = {
            'bug': ['Bug', 'Defect', 'Issue', 'Problem'],
            'task': ['Task', 'Story', 'User Story', 'Feature'],
            'epic': ['Epic'],
            'story': ['Story', 'User Story', 'Feature']
        }

        if issue_type.lower() in issue_type_mapping:
            mapped_types = issue_type_mapping[issue_type.lower()]
            type_conditions = [f"issuetype = \"{t}\"" for t in mapped_types]
            conditions.append(f"({' OR '.join(type_conditions)})")
        else:
            conditions.append(f"issuetype = \"{issue_type}\"")

    if text_search:
        # Use Jira's text search
        conditions.append(f"text ~ \"{text_search}\"")

    if labels:
        for label in labels:
            conditions.append(f"labels = \"{label}\"")

    # Add any additional conditions from kwargs
    for key, value in kwargs.items():
        if value:
            conditions.append(f"{key} = \"{value}\"")

    if not conditions:
        return "ORDER BY updated DESC"

    return " AND ".join(conditions) + " ORDER BY updated DESC"


def parse_natural_language_query(query: str) -> Dict[str, Any]:
    """Parse natural language query into JQL components"""
    query_lower = query.lower()
    params = {}

    # Extract assignee
    if any(phrase in query_lower for phrase in ['assigned to me', 'my issues', 'my tasks']):
        params['assignee'] = 'currentUser()'
    elif 'assigned to' in query_lower:
        # Try to extract specific assignee
        match = re.search(r'assigned to (\w+)', query_lower)
        if match:
            params['assignee'] = match.group(1)

    # Extract priority
    if any(phrase in query_lower for phrase in ['high priority', 'urgent', 'critical']):
        params['priority'] = 'high'
    elif any(phrase in query_lower for phrase in ['low priority', 'minor']):
        params['priority'] = 'low'
    elif 'medium priority' in query_lower:
        params['priority'] = 'medium'

    # Extract issue type
    if any(phrase in query_lower for phrase in ['bug', 'defect', 'issue', 'problem']):
        params['issue_type'] = 'bug'
    elif any(phrase in query_lower for phrase in ['task', 'story', 'feature']):
        params['issue_type'] = 'task'
    elif 'epic' in query_lower:
        params['issue_type'] = 'epic'

    # Extract status
    if any(phrase in query_lower for phrase in ['open', 'in progress', 'todo']):
        params['status'] = 'Open'
    elif any(phrase in query_lower for phrase in ['done', 'closed', 'resolved']):
        params['status'] = 'Done'

    # Extract text search
    # Remove common query words and use the rest for text search
    stop_words = ['show', 'find', 'get', 'list', 'all', 'my', 'the', 'issues', 'tasks', 'bugs', 'with', 'that', 'are', 'assigned', 'to', 'me', 'high', 'low', 'medium', 'priority']
    words = query_lower.split()
    text_words = [word for word in words if word not in stop_words and len(word) > 2]

    if text_words and not any(key in params for key in ['priority', 'issue_type', 'status']):
        params['text_search'] = ' '.join(text_words)

    return params