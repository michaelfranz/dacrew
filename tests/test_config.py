import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from dacrew.config import AppConfig


def test_load_config():
    cfg = AppConfig.load("config.example.yml")
    assert cfg.projects[0].type_status_map["Bug"]["To Do"] == "todo-evaluator"
