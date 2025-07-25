from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from typing import Iterable

COMMANDS = {
    "init": {"subcommands": [], "options": []},
    "codebase": {
        "subcommands": [
            "init", "add", "list", "scan", "index",
            "search", "stats", "current",
            "remove", "clean-embeddings", "purge"
        ],
        "options": []
    },
    "issues": {
        "subcommands": ["list", "show", "create", "embed", "test-connection"],
        "options": {
            "embed": [
                "--force",
                "--limit",
                "--project",
                "--status",
                "--assignee",
                "--incremental",
                "--dry-run"
            ]
        }
    },
    "gen": {
        "subcommands": [],
        "options": [
            "--issue",
            "--dry-run",
            "--auto-commit",
            "--allow-fail",
            "--skip-tests",
            "--branch"
        ]
    },
    "help": {"subcommands": [], "options": []},
    "exit": {"subcommands": [], "options": []},
    "quit": {"subcommands": [], "options": []},
    "bye": {"subcommands": [], "options": []}
}


class DaCrewCompleter(Completer):
    def get_completions(
            self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor.strip()
        words = text.split()

        if len(words) == 0:
            # Suggest top-level commands
            for cmd in COMMANDS:
                yield Completion(cmd, start_position=0)

        elif len(words) == 1:
            # First-level completion: top-level commands
            first_word = words[0]
            if first_word in COMMANDS:
                # Command fully typed, show subcommands
                for sub in COMMANDS[first_word]["subcommands"]:
                    yield Completion(sub, start_position=0)
            else:
                # Suggest matching commands
                for cmd in COMMANDS:
                    if cmd.startswith(first_word):
                        yield Completion(cmd, start_position=-len(first_word))

        elif len(words) == 2:
            first_word, second_word = words
            cmd_info = COMMANDS.get(first_word)

            if cmd_info:
                # If the second word matches a subcommand that has options, show options
                if second_word in cmd_info.get("subcommands", []) and second_word in cmd_info.get("options", {}):
                    for opt in cmd_info["options"][second_word]:
                        yield Completion(opt, start_position=0)
                else:
                    # Otherwise, complete subcommands
                    for sub in cmd_info.get("subcommands", []):
                        if sub.startswith(second_word):
                            yield Completion(sub, start_position=-len(second_word))

        elif len(words) >= 3:
            first_word = words[0]
            subcommand = words[1]
            current = words[-1]
            cmd_info = COMMANDS.get(first_word)

            if cmd_info and subcommand in cmd_info.get("subcommands", []):
                sub_opts = cmd_info.get("options", {}).get(subcommand, [])
                for opt in sub_opts:
                    if opt.startswith(current):
                        yield Completion(opt, start_position=-len(current))