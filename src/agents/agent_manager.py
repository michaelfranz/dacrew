"""Agent Manager for coordinating multiple Jira AI agents"""

import logging
from typing import Dict, Any, Optional

from .jira_action_agent import JiraActionAgent
from .jira_query_agent import JiraQueryAgent
from ..config import Config
from ..jira_client import JiraClient
from ..vector_db.vector_manager import VectorManager

logger = logging.getLogger(__name__)


class AgentManager:
    """Manages and coordinates multiple Jira AI agents"""

    def __init__(self, config: Config, jira_client: JiraClient, vector_manager: VectorManager = None):
        self.config = config
        self.jira_client = jira_client
        self.vector_manager = vector_manager
        self.agents = self._initialize_agents()

    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all agents"""
        try:
            agents = {
                'query': JiraQueryAgent(self.config, self.jira_client, self.vector_manager),
                'action': JiraActionAgent(self.config, self.jira_client)
            }

            logger.info("All agents initialized successfully")
            return agents

        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise

    def process_natural_language_query(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Process a natural language query using appropriate agents"""
        try:
            # Determine intent and route to appropriate agent
            intent = self._determine_intent(query)

            if intent == 'search':
                return self._handle_search_query(query, project)
            elif intent == 'create':
                return self._handle_create_query(query, project)
            elif intent == 'update':
                return self._handle_update_query(query, project)
            elif intent == 'transition':
                return self._handle_transition_query(query, project)
            elif intent == 'sync':
                return self._handle_sync_query(query, project)
            else:
                # Default to search if intent is unclear
                return self._handle_search_query(query, project)

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }

    def _determine_intent(self, query: str) -> str:
        """Determine the intent of the natural language query"""
        query_lower = query.lower()

        # Action keywords
        create_keywords = ['create', 'new', 'add', 'make']
        update_keywords = ['update', 'modify', 'change', 'edit', 'fix']
        transition_keywords = ['move', 'transition', 'close', 'resolve', 'complete', 'start']
        search_keywords = ['find', 'search', 'show', 'list', 'get', 'what', 'which', 'similar']
        sync_keywords = ['sync', 'synchronize', 'update database', 'refresh']

        # Check for sync intent
        if any(keyword in query_lower for keyword in sync_keywords):
            return 'sync'

        # Check for create intent
        if any(keyword in query_lower for keyword in create_keywords):
            return 'create'

        # Check for update intent
        if any(keyword in query_lower for keyword in update_keywords):
            return 'update'

        # Check for transition intent
        if any(keyword in query_lower for keyword in transition_keywords):
            return 'transition'

        # Check for search intent
        if any(keyword in query_lower for keyword in search_keywords):
            return 'search'

        # Default to search
        return 'search'

    def _handle_search_query(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Handle search queries using the Query Agent"""
        try:
            # Enhanced task description for semantic search
            task_description = f"""
            Search for Jira issues based on this query: "{query}"
            
            Instructions:
            1. Analyze the query to understand what the user is looking for
            2. If the query is about finding similar issues or uses conceptual language, use semantic search
            3. If the query is specific (issue keys, exact status, etc.), use traditional JQL search
            4. If semantic search is available, try it first for better results
            5. Provide comprehensive results with relevant issue details
            6. If no specific project is mentioned, use the default project: {project or self.config.project.default_project_key}
            
            Query: {query}
            Project: {project or self.config.project.default_project_key}
            """

            return self.agents['query'].execute_task(task_description)

        except Exception as e:
            logger.error(f"Error handling search query: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_create_query(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Handle create queries using the Action Agent"""
        try:
            task_description = f"""
            Create a new Jira issue based on this request: "{query}"
            
            Instructions:
            1. Extract the issue details from the user's request
            2. Determine appropriate issue type (Task, Bug, Story, etc.)
            3. Create a clear and concise summary
            4. Include relevant description
            5. Use project: {project or self.config.project.default_project_key}
            6. Set appropriate priority if mentioned
            7. Assign to user if mentioned
            
            Request: {query}
            Project: {project or self.config.project.default_project_key}
            """

            return self.agents['action'].execute_task(task_description)

        except Exception as e:
            logger.error(f"Error handling create query: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_update_query(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Handle update queries using the Action Agent"""
        try:
            task_description = f"""
            Update a Jira issue based on this request: "{query}"
            
            Instructions:
            1. Identify which issue to update (extract issue key if mentioned)
            2. Determine what fields need to be updated
            3. Apply the requested changes
            4. Provide confirmation of the update
            
            Request: {query}
            """

            return self.agents['action'].execute_task(task_description)

        except Exception as e:
            logger.error(f"Error handling update query: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_transition_query(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Handle transition queries using the Action Agent"""
        try:
            task_description = f"""
            Transition a Jira issue based on this request: "{query}"
            
            Instructions:
            1. Identify which issue to transition (extract issue key if mentioned)
            2. Determine the target status
            3. Check available transitions
            4. Perform the transition
            5. Provide confirmation
            
            Request: {query}
            """

            return self.agents['action'].execute_task(task_description)

        except Exception as e:
            logger.error(f"Error handling transition query: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_sync_query(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Handle sync queries using the Query Agent"""
        try:
            task_description = f"""
            Sync Jira issues with the vector database based on this request: "{query}"
            
            Instructions:
            1. Determine if this is a full sync or project-specific sync
            2. Use the sync_vector_db tool to update the vector database
            3. Provide status update on the sync operation
            4. Show database statistics after sync
            
            Request: {query}
            Project: {project or 'all projects'}
            """

            return self.agents['query'].execute_task(task_description)

        except Exception as e:
            logger.error(f"Error handling sync query: {e}")
            return {'success': False, 'error': str(e)}

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            'agents_initialized': len(self.agents),
            'available_agents': list(self.agents.keys()),
            'jira_connected': self.jira_client.test_connection(),
            'vector_db_available': self.vector_manager is not None
        }

        if self.vector_manager:
            try:
                vector_stats = self.vector_manager.get_collection_stats()
                status['vector_db_stats'] = vector_stats
            except Exception as e:
                status['vector_db_error'] = str(e)

        return status