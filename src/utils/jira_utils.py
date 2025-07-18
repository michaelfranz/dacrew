"""Utility functions for JIRA operations"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def build_jql_query(
        project: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        issue_type: Optional[str] = None,
        created_after: Optional[datetime] = None,
        updated_after: Optional[datetime] = None,
        text_search: Optional[str] = None,
        labels: Optional[List[str]] = None,
        priority: Optional[str] = None
) -> str:
    """Build JQL query from parameters"""

    conditions = []

    if project:
        conditions.append(f'project = "{project}"')

    if status:
        conditions.append(f'status = "{status}"')

    if assignee:
        if assignee.lower() == 'me':
            conditions.append('assignee = currentUser()')
        elif assignee.lower() == 'unassigned':
            conditions.append('assignee is EMPTY')
        else:
            conditions.append(f'assignee = "{assignee}"')

    if issue_type:
        conditions.append(f'issuetype = "{issue_type}"')

    if created_after:
        date_str = created_after.strftime('%Y-%m-%d')
        conditions.append(f'created >= "{date_str}"')

    if updated_after:
        date_str = updated_after.strftime('%Y-%m-%d')
        conditions.append(f'updated >= "{date_str}"')

    if text_search:
        conditions.append(f'text ~ "{text_search}"')

    if labels:
        label_conditions = [f'labels = "{label}"' for label in labels]
        conditions.append(f'({" OR ".join(label_conditions)})')

    if priority:
        conditions.append(f'priority = "{priority}"')

    return ' AND '.join(conditions) if conditions else 'project is not EMPTY'


def extract_issue_keys(text: str) -> List[str]:
    """Extract JIRA issue keys from text"""
    pattern = r'\b[A-Z]{2,10}-\d+\b'
    return re.findall(pattern, text)


def format_issue_summary(issue: Dict[str, Any]) -> str:
    """Format issue for display"""
    return f"[{issue['key']}] {issue['summary']} ({issue['status']})"


def get_common_statuses() -> List[str]:
    """Get common JIRA statuses"""
    return [
        'To Do', 'In Progress', 'Done', 'Backlog', 'Selected for Development',
        'In Review', 'Testing', 'Closed', 'Resolved', 'Reopened'
    ]


def get_common_priorities() -> List[str]:
    """Get common JIRA priorities"""
    return ['Highest', 'High', 'Medium', 'Low', 'Lowest']


def get_common_issue_types() -> List[str]:
    """Get common JIRA issue types"""
    return ['Task', 'Bug', 'Story', 'Epic', 'Sub-task', 'Improvement']


def parse_relative_date(date_str: str) -> Optional[datetime]:
    """Parse relative date strings like 'last week', 'yesterday', etc."""
    date_str = date_str.lower().strip()
    now = datetime.now()

    if date_str in ['today']:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str in ['yesterday']:
        return now - timedelta(days=1)
    elif date_str in ['last week', 'week ago']:
        return now - timedelta(weeks=1)
    elif date_str in ['last month', 'month ago']:
        return now - timedelta(days=30)
    elif 'days ago' in date_str:
        try:
            days = int(re.findall(r'\d+', date_str)[0])
            return now - timedelta(days=days)
        except (IndexError, ValueError):
            return None
    elif 'weeks ago' in date_str:
        try:
            weeks = int(re.findall(r'\d+', date_str)[0])
            return now - timedelta(weeks=weeks)
        except (IndexError, ValueError):
            return None

    return None


def validate_issue_key(issue_key: str) -> bool:
    """Validate JIRA issue key format"""
    pattern = r'^[A-Z]{2,10}-\d+$'
    return bool(re.match(pattern, issue_key))