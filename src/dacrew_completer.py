import shlex
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from typing import Iterable

COMMANDS = {
    "init": {"subcommands": [], "options": []},
    "issues": {
        "subcommands": ["list", "show", "create", "test-connection"],
        "options": {}
    },
    "embeddings": {
        "subcommands": ["index", "query", "stats", "clean"],
        "options": {
            "index": [
                "--codebase",
                "--issues",
                "--documents"
            ],
            "query": [
                "--codebase",
                "--issues",
                "--documents",
                "--top-k",
            ],
            "stats": [
                "--codebase",
                "--issues",
                "--documents",
            ],
            "clean": [
                "--force",
                "--codebase",
                "--issues",
                "--documents",
            ]
        }
    },
    "agent": {
        "subcommands": ["run", "code"],
        "options": {
            "run": [
                "--issue",
                "--dry-run",
            ],
            "code": [
                "--issue",
                "--dry-run",
                "--auto-commit",
                "--allow-fail",
                "--skip-tests",
                "--branch"
            ]
        }
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

        try:
            words = shlex.split(text)  # Handles quoted arguments as single tokens
        except ValueError:
            words = text.split()  # Fallback if quotes are not closed

        # Current token being completed
        current = document.get_word_before_cursor()

        if len(words) == 0:
            # Suggest top-level commands
            for cmd in COMMANDS:
                yield Completion(cmd, start_position=0)

        elif len(words) == 1:
            first_word = words[0]
            if first_word in COMMANDS:
                # Command fully typed, show subcommands
                for sub in COMMANDS[first_word]["subcommands"]:
                    yield Completion(sub, start_position=0)
            else:
                for cmd in COMMANDS:
                    if cmd.startswith(first_word):
                        yield Completion(cmd, start_position=-len(first_word))

        elif len(words) == 2:
            first_word, second_word = words
            cmd_info = COMMANDS.get(first_word)

            if cmd_info:
                subcommands = cmd_info.get("subcommands", [])
                options = cmd_info.get("options")

                # Subcommand suggestions
                for sub in subcommands:
                    if sub.startswith(second_word):
                        yield Completion(sub, start_position=-len(second_word))

                # Top-level options (if a flat list exists)
                if isinstance(options, list):
                    for opt in options:
                        if opt.startswith(second_word):
                            yield Completion(opt, start_position=-len(second_word))

        else:
            # len(words) >= 3
            first_word = words[0]
            subcommand = words[1]
            cmd_info = COMMANDS.get(first_word)

            if cmd_info and subcommand in cmd_info.get("subcommands", []):
                sub_opts = cmd_info.get("options", {}).get(subcommand, [])
                current = words[-1]

                # Check if we are still in the quoted argument (no completions inside quotes)
                if text.count('"') % 2 == 1 and not current.startswith("--"):
                    return  # Do not suggest options inside an open quote

                # Suggest options starting with current token
                for opt in sub_opts:
                    if opt.startswith(current):
                        yield Completion(opt, start_position=-len(current))