import unittest
from prompt_toolkit.document import Document
from src.dacrew_completer import DaCrewCompleter
from src.dacrew_completer import COMMANDS  # Adjust if COMMANDS is defined elsewhere


class TestDaCrewCompleter(unittest.TestCase):
    def setUp(self):
        self.completer = DaCrewCompleter()

    def get_completions_text(self, text):
        """Helper to return completion texts for a given input string."""
        completions = list(self.completer.get_completions(Document(text), None))
        return [c.text for c in completions]

    def test_top_level_commands(self):
        completions = self.get_completions_text("")
        for cmd in COMMANDS.keys():
            self.assertIn(cmd, completions)

    def test_partial_top_level(self):
        completions = self.get_completions_text("iss")
        self.assertIn("issues", completions)
        self.assertNotIn("codebase", completions)

    def test_subcommands_for_issues(self):
        completions = self.get_completions_text("issues ")
        # It should suggest list, show, create, embed, test-connection
        self.assertIn("list", completions)
        self.assertIn("show", completions)
        self.assertIn("create", completions)
        self.assertIn("embed", completions)

    def test_subcommand_partial_match(self):
        completions = self.get_completions_text("issues l")
        self.assertIn("list", completions)
        self.assertNotIn("show", completions)

    def test_embed_options(self):
        # When user types 'issues embed ' it should show embed options
        completions = self.get_completions_text("issues embed ")
        self.assertIn("--force", completions)
        self.assertIn("-f", completions)
        self.assertIn("--dry-run", completions)

    def test_unknown_command(self):
        completions = self.get_completions_text("foobar")
        # Suggests top-level commands starting with foobar? None should match
        self.assertEqual(len(completions), 0)


if __name__ == '__main__':
    unittest.main()