from typing import Iterable

from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

COMMANDS = {
    "codebase": [
        "init", "add", "list", "scan", "index",
        "search", "stats", "current",
        "remove", "clean-embeddings", "purge"
    ],
    "issues": [
        "list", "show", "create", "test-connection"
    ],
    "gen": [
        "--issue", "-i",
        "--dry-run",
        "--auto-commit", "-c",
        "--allow-fail",
        "--skip-tests",
        "--branch", "-b"
    ],
    "help": [],
    "exit": [],
    "quit": [],
    "bye": []
}

class DaCrewCompleter(Completer):
    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor.strip()
        words = text.split()

        if len(words) == 0:
            for cmd in COMMANDS:
                yield Completion(cmd, start_position=0)

        elif len(words) == 1:
            first_word = words[0]
            if first_word in COMMANDS:
                for sub in COMMANDS[first_word]:
                    yield Completion(sub, start_position=0)
            else:
                for cmd in COMMANDS:
                    yield Completion(cmd, start_position=-len(first_word))

        elif len(words) == 2:
            first_word = words[0]
            second_word = words[1]
            if first_word in COMMANDS:
                for sub in COMMANDS[first_word]:
                    if sub.startswith(second_word):
                        yield Completion(sub, start_position=-len(second_word))


