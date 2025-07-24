# src/workflows/generator.py
import os
import shlex
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def get_current_project_dir() -> Path:
    """
    Resolve the workspace/current directory (symbolic link to the active project).
    """
    return Path(__file__).resolve().parents[2] / "workspace" / "current"


current_dir = get_current_project_dir()


def perform_gen(
        issue_key: str,
        auto_commit: bool = False,
        allow_fail: bool = False,
        dry_run: bool = False,
        skip_tests: bool = False,
        branch: str = None
):
    """
    Full pipeline for generating code for a single JIRA requirement.
    """
    console.print(Panel.fit(f"✨ Generating code for issue: [cyan]{issue_key}[/cyan]", border_style="blue"))

    issue_info = fetch_issue_info(issue_key)
    if not issue_info:
        console.print(f"❌ Could not fetch issue: {issue_key}", style="red")
        return

    console.print(f"Title: [yellow]{issue_info['title']}[/yellow]")
    console.print(f"Status: [green]{issue_info['status']}[/green]")
    console.print(f"Labels: {', '.join(issue_info['labels'])}")

    if dry_run:
        console.print("\n[bold cyan]--- DRY RUN: Generation plan ---[/bold cyan]")
        preview_generation(issue_info)
        return

    branch_name = branch or create_branch_name(issue_info)
    if not create_branch(branch_name):
        console.print(f"❌ Failed to create branch: {branch_name}", style="red")
        return
    console.print(f"🌱 Created branch: [cyan]{branch_name}[/cyan]")

    generate_code(issue_info)

    build_success = True
    test_success = True
    if not skip_tests:
        build_success = run_build()
        if build_success:
            test_success = run_tests()
        else:
            test_success = False

    report_results(build_success, test_success)

    if auto_commit:
        commit_and_push(branch_name, issue_info, force=allow_fail or (build_success and test_success))
    else:
        console.print("\n💡 To commit and push manually, run:", style="cyan")
        console.print(f"   git add . && git commit -m \"Implementing {issue_info['key']}: {issue_info['title']}\"")
        console.print(f"   git push -u origin {branch_name}")


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def fetch_issue_info(issue_key: str):
    return {
        "key": issue_key,
        "title": "Improve login flow",
        "status": "Ready for Dev",
        "labels": ["requirement", "frontend"]
    }


def create_branch_name(issue_info: dict):
    prefix = os.getenv("BRANCH_PREFIX", "feature/")
    sanitized_title = issue_info["title"].lower().replace(" ", "-").replace("/", "-")
    return f"{prefix}{issue_info['key']}-{sanitized_title}"


def create_branch(branch_name: str):
    try:
        subprocess.check_call(["git", "checkout", "-b", branch_name], cwd=current_dir)
        return True
    except subprocess.CalledProcessError:
        return False


def preview_generation(issue_info: dict):
    main_dir = f"{current_dir}{os.getenv('MAIN_CODE_DIR', 'src/main/java')}"
    test_dir = f"{current_dir}{os.getenv('TEST_CODE_DIR', 'src/test/java')}"
    console.print(f"Main code will be placed in: [cyan]{main_dir}[/cyan]")
    console.print(f"Test code will be placed in: [cyan]{test_dir}[/cyan]")
    console.print(f"Will run build: {current_dir}{os.getenv('BUILD_COMMAND', './gradlew build')}")
    console.print(f"Will run tests: {current_dir}{os.getenv('TEST_COMMAND', './gradlew test')}")


def generate_code(issue_info: dict):
    console.print("🛠 Generating code...")
    main_dir = f"{current_dir}{os.getenv('MAIN_CODE_DIR', 'src/main/java')}"
    test_dir = f"{current_dir}{os.getenv('TEST_CODE_DIR', 'src/test/java')}"
    os.makedirs(main_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    (Path(main_dir) / "GeneratedFile.java").write_text("// TODO: Generated code\n")
    (Path(test_dir) / "GeneratedFileTest.java").write_text("// TODO: Generated test code\n")


def run_build():
    build_cmd = os.getenv('BUILD_COMMAND', './gradlew build')
    console.print(f"🏗 Running build: [cyan]{build_cmd}[/cyan]")
    return run_shell(build_cmd)


def run_tests():
    test_cmd = os.getenv('TEST_COMMAND', './gradlew test')
    console.print(f"🧪 Running tests: [cyan]{test_cmd}[/cyan]")
    return run_shell(test_cmd)


def run_shell(command):
    try:
        subprocess.check_call(shlex.split(command), cwd=current_dir)
        return True
    except subprocess.CalledProcessError:
        return False


def report_results(build_success: bool, test_success: bool):
    console.print("\n[bold cyan]--- Build/Test Results ---[/bold cyan]")
    console.print(f"Build: {'✅ Passed' if build_success else '❌ Failed'}")
    if build_success:
        console.print(f"Tests: {'✅ Passed' if test_success else '❌ Failed'}")


def commit_and_push(branch_name: str, issue_info: dict, force=False):
    if not force:
        console.print("\n💡 Tests failed. Skipping auto-commit unless --allow-fail is set.", style="yellow")
        return

    commit_msg = os.getenv("COMMIT_TEMPLATE", "Implementing {ISSUE_ID}: {ISSUE_TITLE}") \
        .replace("{ISSUE_ID}", issue_info["key"]) \
        .replace("{ISSUE_TITLE}", issue_info["title"])

    console.print(f"\n🔐 Committing changes with message: [cyan]{commit_msg}[/cyan]")
    try:
        subprocess.check_call(["git", "add", "."], cwd=current_dir)
        subprocess.check_call(["git", "commit", "-m", commit_msg], cwd=current_dir)
        subprocess.check_call(["git", "push", "-u", "origin", branch_name], cwd=current_dir)
        console.print(f"🚀 Code pushed to remote branch [cyan]{branch_name}[/cyan]")
    except subprocess.CalledProcessError:
        console.print("❌ Git commit/push failed.", style="red")
