from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class PipelinePlan:
    """
    Describes what the CI pipeline should execute.
    """

    install_commands: List[str]
    build_commands: List[str]
    test_commands: List[str]
    has_tests: bool
    test_framework: str | None


class ProjectDetectionError(Exception):
    pass


def detect_python_project(repo_dir: str) -> PipelinePlan:
    """
    Detect the build and test strategy for a Python repository.

    Rules:

    1. Install dependencies if dependency files exist.
    2. Always perform a Python syntax/build check.
    3. If tests exist, execute them.
    4. If tests do not exist, build-only mode is used.
    """

    root = Path(repo_dir)

    # =============================================================
    # Dependency detection
    # =============================================================

    install_commands = []

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
    }
    
    
    dependency_files = []
    project_files = []
    
    
    for path in root.rglob("*"):
    
        if not path.is_file():
            continue
        
        if any(
            ignored in path.parts
            for ignored in ignored_dirs
        ):
            continue
        
        if (
            path.name == "requirements.txt"
            or path.name == "requirements-dev.txt"
            or (
                path.name.startswith("requirements-")
                and path.name.endswith(".txt")
            )
        ):
            dependency_files.append(path)
    
        elif path.name in {
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
        }:
            project_files.append(path)
    
    
    for dependency_file in sorted(dependency_files):
    
        install_commands.append(
            f"pip install -r '{dependency_file.relative_to(root)}'"
        )
    
    
    requirement_directories = {
        path.parent.resolve()
        for path in dependency_files
    }
    
    
    for project_file in sorted(project_files):
    
        project_directory = project_file.parent.resolve()
    
        if project_directory in requirement_directories:
            continue
        
        relative_directory = (
            project_directory.relative_to(root)
        )
    
        install_commands.append(
            f"pip install -e '{relative_directory}'"
        )
    
    # ---------------------------------------------------------
    # BUILD
    # ---------------------------------------------------------
    #
    # Python does not have one universal build command.
    #
    # compileall verifies that Python source files can be
    # compiled successfully and catches syntax errors.
    # ---------------------------------------------------------

    build_commands = [
        "python -m compileall -q ."
    ]

    # ---------------------------------------------------------
    # TEST detection
    # ---------------------------------------------------------

    test_files = []

    for pattern in ("test_*.py", "*_test.py"):
        test_files.extend(root.rglob(pattern))

    # Ignore files inside virtual environments and git metadata.
    test_files = [
        path
        for path in test_files
        if not any(
            ignored in path.parts
            for ignored in (
                ".git",
                ".venv",
                "venv",
                "__pycache__",
            )
        )
    ]

    has_tests_directory = (root / "tests").is_dir()

    # Only consider the tests directory meaningful when it
    # actually contains Python test files.
    tests_directory_has_python_files = False

    if has_tests_directory:
        tests_directory_has_python_files = any(
            path.suffix == ".py"
            for path in (root / "tests").rglob("*.py")
        )

    has_tests = bool(test_files)

    if tests_directory_has_python_files:
        has_tests = True

    # ---------------------------------------------------------
    # Test framework detection
    # ---------------------------------------------------------

    test_framework = None
    test_commands = []

    if has_tests:

        pytest_config = (
            (root / "pytest.ini").exists()
            or (root / "tox.ini").exists()
        )

        pyproject = root / "pyproject.toml"

        if pyproject.exists():
            try:
                content = pyproject.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                if (
                    "[tool.pytest" in content
                    or "pytest" in content.lower()
                ):
                    pytest_config = True

            except OSError:
                pass

        # Look for pytest usage inside test files.
        pytest_usage = False

        for test_file in test_files:
            try:
                content = test_file.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                if (
                    "import pytest" in content
                    or "from pytest" in content
                ):
                    pytest_usage = True
                    break

            except OSError:
                continue

        if pytest_config or pytest_usage or has_tests_directory:
            test_framework = "pytest"

            # Ensure pytest exists even if the repository did
            # not declare it in requirements.txt.
            install_commands.append(
                "pip install pytest"
            )

            test_commands.append(
                "python -m pytest -v"
            )

        else:
            test_framework = "unittest"

            test_commands.append(
                "python -m unittest discover -v"
            )

    return PipelinePlan(
        install_commands=install_commands,
        build_commands=build_commands,
        test_commands=test_commands,
        has_tests=has_tests,
        test_framework=test_framework,
    )