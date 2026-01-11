"""Autonomous test runner for minions.

Detects project type and runs appropriate test commands.
Reports results back without user interaction.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# Test commands by project type (in order of preference)
TEST_COMMANDS = {
    "python": [
        ("pytest", ["pytest", "-v", "--tb=short"]),
        ("unittest", ["python", "-m", "unittest", "discover"]),
    ],
    "node": [
        ("npm", ["npm", "test"]),
        ("yarn", ["yarn", "test"]),
        ("pnpm", ["pnpm", "test"]),
    ],
    "rust": [
        ("cargo", ["cargo", "test"]),
    ],
    "go": [
        ("go", ["go", "test", "./..."]),
    ],
}

# Project type detection by marker files
PROJECT_MARKERS = {
    "python": ["pyproject.toml", "setup.py", "pytest.ini", "requirements.txt"],
    "node": ["package.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
}


@dataclass
class TestResult:
    """Result of running tests."""

    success: bool
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    error: str | None = None


@dataclass
class MinionTestRunner:
    """Autonomous test runner."""

    repo_root: Path
    timeout_seconds: int = 300  # 5 min default
    project_type: str | None = None
    _detected: bool = field(default=False, init=False)

    def __post_init__(self):
        self.repo_root = Path(self.repo_root).resolve()

    def detect_project_type(self) -> str | None:
        """Detect project type from marker files."""
        if self._detected:
            return self.project_type

        for ptype, markers in PROJECT_MARKERS.items():
            for marker in markers:
                if (self.repo_root / marker).exists():
                    self.project_type = ptype
                    self._detected = True
                    return ptype

        self._detected = True
        return None

    def get_test_command(self) -> tuple[str, list[str]] | None:
        """Get the appropriate test command for this project."""
        ptype = self.detect_project_type()
        if not ptype:
            return None

        commands = TEST_COMMANDS.get(ptype, [])
        for name, cmd in commands:
            # Check if the command is available
            if shutil.which(cmd[0]):
                return (name, cmd)

        return None

    async def run(self, test_path: str | None = None) -> TestResult:
        """Run tests and return results.

        Args:
            test_path: Optional specific test file/directory to run

        Returns:
            TestResult with pass/fail status and output
        """
        import time

        start = time.time()

        # Detect command
        cmd_info = self.get_test_command()
        if not cmd_info:
            return TestResult(
                success=False,
                command="",
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=0,
                error=f"Could not detect project type or find test command in {self.repo_root}",
            )

        name, cmd = cmd_info

        # Add specific test path if provided
        if test_path:
            cmd = cmd + [test_path]

        # Run the command
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.repo_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return TestResult(
                    success=False,
                    command=" ".join(cmd),
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    duration_ms=int((time.time() - start) * 1000),
                    error=f"Test timed out after {self.timeout_seconds}s",
                )

            duration_ms = int((time.time() - start) * 1000)
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Parse test counts from output
            passed, failed, skipped = self._parse_test_counts(stdout_str + stderr_str)

            return TestResult(
                success=proc.returncode == 0,
                command=" ".join(cmd),
                exit_code=proc.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                tests_passed=passed,
                tests_failed=failed,
                tests_skipped=skipped,
            )

        except Exception as e:
            return TestResult(
                success=False,
                command=" ".join(cmd),
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )

    def _parse_test_counts(self, output: str) -> tuple[int, int, int]:
        """Parse test counts from output. Returns (passed, failed, skipped)."""
        import re

        passed = failed = skipped = 0

        # pytest format: "5 passed, 2 failed, 1 skipped"
        pytest_match = re.search(
            r"(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) skipped)?",
            output,
        )
        if pytest_match:
            passed = int(pytest_match.group(1) or 0)
            failed = int(pytest_match.group(2) or 0)
            skipped = int(pytest_match.group(3) or 0)
            return passed, failed, skipped

        # Jest/Mocha format: "Tests: 5 passed, 2 failed"
        jest_match = re.search(
            r"Tests:\s*(\d+) passed(?:.*?(\d+) failed)?",
            output,
        )
        if jest_match:
            passed = int(jest_match.group(1) or 0)
            failed = int(jest_match.group(2) or 0)
            return passed, failed, skipped

        # Go format: "ok" or "FAIL"
        if "PASS" in output or "ok " in output:
            passed = 1
        if "FAIL" in output:
            failed = 1

        # Rust format: "test result: ok. X passed"
        rust_match = re.search(r"(\d+) passed.*?(\d+) failed", output)
        if rust_match:
            passed = int(rust_match.group(1) or 0)
            failed = int(rust_match.group(2) or 0)

        return passed, failed, skipped


async def run_tests(
    repo_root: str | Path = ".",
    test_path: str | None = None,
    timeout: int = 300,
) -> TestResult:
    """Convenience function to run tests.

    Args:
        repo_root: Repository root directory
        test_path: Optional specific test to run
        timeout: Timeout in seconds

    Returns:
        TestResult with status and output
    """
    runner = MinionTestRunner(repo_root=repo_root, timeout_seconds=timeout)
    return await runner.run(test_path)


__all__ = ["MinionTestRunner", "TestResult", "run_tests"]
