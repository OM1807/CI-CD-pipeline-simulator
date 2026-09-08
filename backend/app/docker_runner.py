import os
import shlex
import threading

import docker

from .detector import detect_python_project


client = docker.from_env()

BUILD_TIMEOUT_SECONDS = int(
    os.getenv("BUILD_TIMEOUT_SECONDS", "300")
)


def _create_pipeline_script() -> str:
    """
    Creates the script that runs INSIDE the isolated Docker
    build container.

    The script:
        1. Detects dependencies
        2. Installs dependencies
        3. Performs build/syntax validation
        4. Detects tests
        5. Runs tests if present
        6. Exits with the correct status code
    """

    return r'''
from pathlib import Path
import subprocess
import sys


ROOT = Path("/app")


def run_command(command, stage):
    print("", flush=True)
    print("=" * 50, flush=True)
    print(f"{stage}", flush=True)
    print("=" * 50, flush=True)
    print(f"Running: {command}", flush=True)
    print("", flush=True)

    process = subprocess.Popen(
        command,
        shell=True,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout:
        print(line, end="", flush=True)

    process.wait()

    print("", flush=True)
    print(
        f"{stage} exit code: {process.returncode}",
        flush=True
    )

    return process.returncode


# =============================================================
# Dependency detection
# =============================================================

install_commands = []

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
}


def find_python_files():
    """
    Recursively discover Python dependency/project files.

    This supports normal repositories as well as monorepos,
    for example:

        requirements.txt
        apps/api/requirements.txt
        apps/api/pyproject.toml
        services/backend/setup.py
    """

    dependency_files = []
    project_files = []

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        if any(
            ignored in path.parts
            for ignored in IGNORED_DIRS
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

    return (
        sorted(dependency_files),
        sorted(project_files),
    )


dependency_files, project_files = find_python_files()


print("", flush=True)
print("=" * 50, flush=True)
print("DEPENDENCY DISCOVERY", flush=True)
print("=" * 50, flush=True)


for dependency_file in dependency_files:

    print(
        f"Found dependency file: {dependency_file}",
        flush=True
    )

    install_commands.append(
        f"pip install -r '{dependency_file}'"
    )


# Keep track of directories that already have a
# requirements file. We don't need to install the same
# Python project twice.
requirement_directories = {
    path.parent.resolve()
    for path in dependency_files
}


for project_file in project_files:

    project_directory = project_file.parent.resolve()

    if project_directory in requirement_directories:
        continue

    print(
        f"Found Python project: {project_file}",
        flush=True
    )

    install_commands.append(
        f"pip install -e '{project_directory}'"
    )


if not install_commands:

    print(
        "No Python dependency/project files found.",
        flush=True
    )


# =============================================================
# Install dependencies
# =============================================================

for command in install_commands:

    exit_code = run_command(
        command,
        "DEPENDENCY INSTALLATION"
    )

    if exit_code != 0:

        print(
            "\nDEPENDENCY INSTALLATION FAILED",
            flush=True
        )

        sys.exit(exit_code)


# =============================================================
# BUILD
# =============================================================

print("", flush=True)
print("=" * 50, flush=True)
print("BUILD CHECK", flush=True)
print("=" * 50, flush=True)

print(
    "Running Python compilation check...",
    flush=True
)

build_command = "python -m compileall -q ."

build_exit_code = run_command(
    build_command,
    "BUILD CHECK"
)

if build_exit_code != 0:

    print("", flush=True)
    print("=" * 50, flush=True)
    print("BUILD FAILED", flush=True)
    print("=" * 50, flush=True)

    sys.exit(build_exit_code)


print("", flush=True)
print("=" * 50, flush=True)
print("BUILD PASSED", flush=True)
print("=" * 50, flush=True)


# =============================================================
# TEST DETECTION
# =============================================================

test_files = []

for pattern in ("test_*.py", "*_test.py"):

    test_files.extend(
        ROOT.rglob(pattern)
    )


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


has_tests_directory = (
    ROOT / "tests"
).is_dir()


tests_directory_has_python_files = False

if has_tests_directory:

    tests_directory_has_python_files = any(
        path.suffix == ".py"
        for path in (ROOT / "tests").rglob("*.py")
    )


has_tests = (
    len(test_files) > 0
    or tests_directory_has_python_files
)


# =============================================================
# NO TESTS
# =============================================================

if not has_tests:

    print("", flush=True)
    print("=" * 50, flush=True)
    print("NO TEST SUITE DETECTED", flush=True)
    print("=" * 50, flush=True)

    print(
        "No tests were found in this repository.",
        flush=True
    )

    print(
        "Build-only mode: build validation completed successfully.",
        flush=True
    )

    print(
        "FINAL RESULT: BUILD PASSED",
        flush=True
    )

    sys.exit(0)


# =============================================================
# TEST FRAMEWORK DETECTION
# =============================================================

pytest_config = (
    (ROOT / "pytest.ini").exists()
    or (ROOT / "tox.ini").exists()
)

pyproject = ROOT / "pyproject.toml"

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


# =============================================================
# PYTEST
# =============================================================

if pytest_config or pytest_usage or has_tests_directory:

    print("", flush=True)
    print("=" * 50, flush=True)
    print("TEST SUITE DETECTED", flush=True)
    print("Framework: pytest", flush=True)
    print("=" * 50, flush=True)

    # Make sure pytest is available.
    pytest_install = run_command(
        "pip install pytest",
        "TEST FRAMEWORK SETUP"
    )

    if pytest_install != 0:

        print(
            "\nFailed to install pytest.",
            flush=True
        )

        sys.exit(pytest_install)

    test_exit_code = run_command(
        "python -m pytest -v",
        "TEST EXECUTION"
    )


# =============================================================
# UNITTEST
# =============================================================

else:

    print("", flush=True)
    print("=" * 50, flush=True)
    print("TEST SUITE DETECTED", flush=True)
    print("Framework: unittest", flush=True)
    print("=" * 50, flush=True)

    test_exit_code = run_command(
        "python -m unittest discover -v",
        "TEST EXECUTION"
    )


# =============================================================
# FINAL RESULT
# =============================================================

if test_exit_code == 0:

    print("", flush=True)
    print("=" * 50, flush=True)
    print("ALL TESTS PASSED", flush=True)
    print("FINAL RESULT: BUILD + TESTS PASSED", flush=True)
    print("=" * 50, flush=True)

    sys.exit(0)


print("", flush=True)
print("=" * 50, flush=True)
print("TESTS FAILED", flush=True)
print(
    f"FINAL RESULT: TESTS FAILED "
    f"(exit code {test_exit_code})",
    flush=True
)
print("=" * 50, flush=True)

sys.exit(test_exit_code)
'''


def run_in_docker(
    image,
    repo_url,
    branch,
    steps,
    log_callback,
):
    """
    Execute one build inside a fresh isolated Docker container.

    If explicit steps are provided:
        clone -> execute those steps

    Otherwise:
        clone -> automatic build/test pipeline
    """

    repo_url_escaped = shlex.quote(repo_url)
    branch_escaped = shlex.quote(branch)

    # ---------------------------------------------------------
    # Clone exact branch
    # ---------------------------------------------------------

    clone_command = (
        "apt-get update && "
        "DEBIAN_FRONTEND=noninteractive "
        "apt-get install -y git && "
        f"git clone "
        f"--branch {branch_escaped} "
        f"--single-branch "
        f"{repo_url_escaped} ."
    )

    # ---------------------------------------------------------
    # Explicit steps
    # ---------------------------------------------------------

    if steps:

        commands = [
            clone_command,
            *steps,
        ]

        joined_command = " && ".join(commands)

    # ---------------------------------------------------------
    # Automatic pipeline
    # ---------------------------------------------------------

    else:

        # Encode the Python pipeline script safely.
        import base64

        script = _create_pipeline_script()

        encoded_script = base64.b64encode(
            script.encode("utf-8")
        ).decode("ascii")

        create_script_command = (
            "python -c "
            + shlex.quote(
                "import base64; "
                "open('/tmp/ci_pipeline.py', 'wb').write("
                f"base64.b64decode('{encoded_script}')"
                ")"
            )
        )

        joined_command = (
            clone_command
            + " && "
            + create_script_command
            + " && "
            + "python /tmp/ci_pipeline.py"
        )

    sh_cmd = f"sh -c {shlex.quote(joined_command)}"

    log_callback(
        "\n========================================\n"
        "ISOLATED DOCKER BUILD\n"
        "========================================\n"
        f"Image: {image}\n"
        f"Repository: {repo_url}\n"
        f"Branch: {branch}\n"
        f"Timeout: {BUILD_TIMEOUT_SECONDS}s\n"
        "========================================\n\n"
    )

    container = None
    log_thread = None

    try:

        # -----------------------------------------------------
        # Fresh container per build
        # -----------------------------------------------------

        container = client.containers.run(
            image=image,
            command=sh_cmd,
            detach=True,
            working_dir="/app",
        )

        log_callback(
            f"Docker container started: "
            f"{container.short_id}\n\n"
        )

        # -----------------------------------------------------
        # Stream logs in a separate thread.
        #
        # This is important because container.logs() blocks
        # until the container exits.
        # -----------------------------------------------------

        def stream_logs():

            try:

                for line in container.logs(
                    stream=True,
                    stdout=True,
                    stderr=True,
                ):

                    log_callback(
                        line.decode(
                            "utf-8",
                            errors="replace"
                        )
                    )

            except Exception as exc:

                log_callback(
                    f"\nLog streaming error: {exc}\n"
                )

        log_thread = threading.Thread(
            target=stream_logs,
            daemon=True,
        )

        log_thread.start()

        # -----------------------------------------------------
        # Wait with timeout
        # -----------------------------------------------------

        try:

            result = container.wait(
                timeout=BUILD_TIMEOUT_SECONDS
            )

            exit_code = result["StatusCode"]

        except Exception as exc:

            log_callback(
                "\n========================================\n"
                "BUILD TIMEOUT\n"
                f"Build exceeded {BUILD_TIMEOUT_SECONDS} seconds.\n"
                f"Reason: {exc}\n"
                "Stopping container...\n"
                "========================================\n"
            )

            try:
                container.stop(timeout=5)
            except Exception:
                pass

            return 124

        # Give the log thread time to finish after the container exits.
        if log_thread:
            log_thread.join(timeout=10)

        log_callback(
            f"\nDocker container finished.\n"
            f"Exit code: {exit_code}\n"
        )

        return exit_code

    finally:

        # -----------------------------------------------------
        # Always remove build container.
        # -----------------------------------------------------

        if container is not None:

            try:

                container.remove(
                    force=True
                )

                log_callback(
                    f"Container {container.short_id} "
                    "removed successfully.\n"
                )

            except Exception as exc:

                log_callback(
                    f"Warning: failed to remove container: "
                    f"{exc}\n"
                )