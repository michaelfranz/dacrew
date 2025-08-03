from typing import Any

from rich import Console

from config import Config, CrewAgentConfig
from .base_task_runner import BaseTaskRunner


console = Console()
config = Config.load()

class CodingTaskRunner(BaseTaskRunner):
    def __init__(self, agent_config: CrewAgentConfig):
        super.__init__(super, config, agent_config)



    def _pre_agent_action(self, issue_date: dict[str, Any]):
        pass


    def _post_agent_action(self, issue_date: dict[str, Any]):
        pass
