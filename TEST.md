# DaCrew Testing Matrix

This document tracks the testing status of all DaCrew command-line features for regression testing purposes.

## Features Testing Status

| Feature                     | Manually Tested | Unit Tested | Notes                                                                     |
|-----------------------------|-----------------|-------------|---------------------------------------------------------------------------|
| **Connection Management**   |                 |             |                                                                           |
| Test Jira connection        | ✅               | ✅           | `dacrew test-connection` - Validates Jira connectivity and authentication |
| Test issues connection      | ✅               | ✅           | `dacrew issues test-connection` - Specific Jira issues API validation     |
| **Jira Issues Management**  |                 |             |                                                                           |
| List issues                 | ✅               | ✅           | `dacrew issues list` - Fetches and displays Jira issues with filtering    |
| Show specific issue         | ✅               | ✅           | `dacrew issues show <issue-key>` - Displays detailed issue information    |
| Create new issue            | ❌               | ❌           | `dacrew issues create` - Interactive issue creation workflow              |
| **Workspace Management**    |                 |             |                                                                           |
| Initialize workspace        | ✅               | ❌           | `dacrew codebase init` - Sets up new workspace configuration              |
| **Repository Management**   |                 |             |                                                                           |
| Add repository              | ✅               | ❌           | `dacrew codebase add` - Adds new repository to workspace                  |
| List repositories           | ✅               | ❌           | `dacrew codebase list` - Shows all configured repositories                |
| Show current repository     | ✅               | ❌           | `dacrew codebase current` - Displays active repository details            |
| Switch repository           | ✅               | ❌           | `dacrew codebase switch` - Changes active repository context              |
| Remove repository           | ✅               | ❌           | `dacrew codebase remove` - Removes repository from workspace              |
| **Codebase Analysis**       |                 |             |                                                                           |
| Scan codebase               | ❌               | ❌           | `dacrew codebase scan` - Analyzes code structure and dependencies         |
| Index codebase              | ❌               | ❌           | `dacrew codebase index` - Creates searchable embeddings index             |
| Search codebase             | ❌               | ❌           | `dacrew codebase search` - Semantic search across indexed code            |
| Show codebase statistics    | ❌               | ❌           | `dacrew codebase stats` - Displays codebase metrics and analysis          |
| **Configuration & Setup**   |                 |             |                                                                           |
| Environment configuration   | ❌               | ❌           | Proper handling of .env files and API keys                                |
| Error handling & validation | ❌               | ❌           | Input validation and graceful error handling                              |
| Logging system              | ❌               | ❌           | Comprehensive logging across all operations                               |
| **CLI User Experience**     |                 |             |                                                                           |
| Help system                 | ❌               | ❌           | `--help` documentation for all commands                                   |
| Command completion          | ❌               | ❌           | Tab completion and command suggestions                                    |
| Progress indicators         | ❌               | ❌           | Progress bars and status updates for long operations                      |

## Testing Legend

- ❌ Not tested
- ⚠️ Partially tested
- ✅ Thoroughly tested

## Testing Guidelines

1. **Manual Testing**: Each feature should be manually tested to verify:
    - Command executes without errors
    - Output is as expected
    - User experience is smooth
    - Error messages are helpful

2. **Unit Testing**: Each feature should have automated unit tests covering:
    - Happy path scenarios
    - Error conditions
    - Edge cases
    - Input validation
    - Mocked external dependencies

3. **Integration Testing**: Should verify:
    - Command-line interface behavior
    - External service connections (Jira, file system)
    - Configuration handling

4. Update the testing columns as testing progresses:
    - Use ❌ for untested features
    - Use ⚠️ for partially tested features
    - Use ✅ for thoroughly tested features

5. Add specific notes about test coverage, known issues, or special considerations in the Notes column.