"""Safety constraints for autonomous minion execution.

Provides denylist, allowlist, and path sandboxing to prevent dangerous operations.
No human gates - minions fail safely and report errors.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

# Commands that are NEVER allowed
DENYLIST_COMMANDS = [
    # Destructive file operations
    "rm -rf",
    "rm -fr",
    "rmdir",
    "del /f",
    "del /s",
    # Privilege escalation
    "sudo",
    "su ",
    "doas",
    "runas",
    # System modification
    "chmod 777",
    "chown",
    "mkfs",
    "fdisk",
    "dd if=",
    # Network dangers
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
    "curl -o- | bash",
    # Git dangers
    "git push --force",
    "git push -f",
    "git reset --hard",
    "git clean -fd",
    # Package managers with sudo
    "sudo apt",
    "sudo yum",
    "sudo dnf",
    "sudo pacman",
    "sudo brew",
    # Env/secrets
    "export AWS_",
    "export GITHUB_TOKEN",
    "printenv",
    # Shell escapes
    "eval ",
    "exec ",
    "; rm ",
    "&& rm ",
    "| rm ",
]

# Patterns that indicate dangerous commands
DENYLIST_PATTERNS = [
    r"rm\s+-[a-z]*r[a-z]*f",  # rm with -rf in any order
    r"rm\s+-[a-z]*f[a-z]*r",  # rm with -fr in any order
    r">\s*/dev/sd",  # Writing to disk devices
    r">\s*/etc/",  # Writing to system config
    r"curl.*\|\s*(ba)?sh",  # Pipe curl to shell
    r"wget.*\|\s*(ba)?sh",  # Pipe wget to shell
    r"\$\(.*\)",  # Command substitution (risky)
    r"`.*`",  # Backtick command substitution
]

# Commands explicitly allowed for tests
ALLOWLIST_TEST_COMMANDS = [
    "pytest",
    "python -m pytest",
    "python -m unittest",
    "npm test",
    "npm run test",
    "yarn test",
    "pnpm test",
    "cargo test",
    "go test",
    "jest",
    "mocha",
    "vitest",
    "rspec",
    "mix test",
]

# File patterns that should never be modified
PROTECTED_FILE_PATTERNS = [
    r"\.env$",
    r"\.env\.",
    r"credentials",
    r"secrets?\.",
    r"\.pem$",
    r"\.key$",
    r"id_rsa",
    r"id_ed25519",
    r"\.ssh/",
    r"\.aws/",
    r"\.docker/config\.json",
]


@dataclass
class SafetyCheck:
    """Result of a safety check."""

    allowed: bool
    reason: str
    matched_rule: str | None = None


@dataclass
class SafetyGuard:
    """Safety constraints for minion execution."""

    repo_root: Path
    allow_shell: bool = False
    custom_denylist: list[str] = field(default_factory=list)
    custom_allowlist: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.repo_root = Path(self.repo_root).resolve()

    def check_command(self, command: str) -> SafetyCheck:
        """Check if a shell command is safe to execute.

        Args:
            command: Shell command to check

        Returns:
            SafetyCheck with allowed status and reason
        """
        if not self.allow_shell:
            return SafetyCheck(
                allowed=False,
                reason="Shell commands disabled",
            )

        cmd_lower = command.lower()

        # Check custom allowlist first (takes priority)
        for allowed in self.custom_allowlist:
            if allowed.lower() in cmd_lower:
                return SafetyCheck(
                    allowed=True,
                    reason="Matched custom allowlist",
                    matched_rule=allowed,
                )

        # Check test commands allowlist
        for allowed in ALLOWLIST_TEST_COMMANDS:
            if cmd_lower.startswith(allowed.lower()):
                return SafetyCheck(
                    allowed=True,
                    reason="Matched test command allowlist",
                    matched_rule=allowed,
                )

        # Check custom denylist
        for denied in self.custom_denylist:
            if denied.lower() in cmd_lower:
                return SafetyCheck(
                    allowed=False,
                    reason="Matched custom denylist",
                    matched_rule=denied,
                )

        # Check global denylist
        for denied in DENYLIST_COMMANDS:
            if denied.lower() in cmd_lower:
                return SafetyCheck(
                    allowed=False,
                    reason="Matched denylist command",
                    matched_rule=denied,
                )

        # Check denylist patterns
        for pattern in DENYLIST_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyCheck(
                    allowed=False,
                    reason="Matched denylist pattern",
                    matched_rule=pattern,
                )

        # Default: allow if shell is enabled and no denylists matched
        return SafetyCheck(
            allowed=True,
            reason="No denylist matches",
        )

    def check_path(self, path: str | Path) -> SafetyCheck:
        """Check if a file path is safe to access/modify.

        Args:
            path: File path to check

        Returns:
            SafetyCheck with allowed status and reason
        """
        try:
            resolved = Path(path).resolve()
        except (OSError, ValueError) as e:
            return SafetyCheck(
                allowed=False,
                reason=f"Invalid path: {e}",
            )

        # Check if within repo root (sandboxing)
        if not str(resolved).startswith(str(self.repo_root)):
            return SafetyCheck(
                allowed=False,
                reason="Path outside repo root",
                matched_rule=str(self.repo_root),
            )

        # Check protected file patterns
        path_str = str(resolved)
        for pattern in PROTECTED_FILE_PATTERNS:
            if re.search(pattern, path_str, re.IGNORECASE):
                return SafetyCheck(
                    allowed=False,
                    reason="Protected file pattern",
                    matched_rule=pattern,
                )

        return SafetyCheck(
            allowed=True,
            reason="Path within repo root and not protected",
        )

    def check_file_write(self, path: str | Path, content: str) -> SafetyCheck:
        """Check if writing content to a file is safe.

        Args:
            path: File path
            content: Content to write

        Returns:
            SafetyCheck with allowed status and reason
        """
        # First check the path
        path_check = self.check_path(path)
        if not path_check.allowed:
            return path_check

        # Check for secrets/credentials in content
        secret_patterns = [
            r"-----BEGIN [A-Z]+ PRIVATE KEY-----",
            r"AKIA[0-9A-Z]{16}",  # AWS access key
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub token
            r"sk-[a-zA-Z0-9]{48}",  # OpenAI key
        ]

        for pattern in secret_patterns:
            if re.search(pattern, content):
                return SafetyCheck(
                    allowed=False,
                    reason="Content contains potential secrets",
                    matched_rule=pattern,
                )

        return SafetyCheck(
            allowed=True,
            reason="File write allowed",
        )

    def sanitize_command(self, command: str) -> str | None:
        """Attempt to sanitize a command, return None if unsafe.

        Args:
            command: Command to sanitize

        Returns:
            Sanitized command or None if cannot be made safe
        """
        check = self.check_command(command)
        if not check.allowed:
            return None

        # Basic sanitization
        try:
            parts = shlex.split(command)
            return shlex.join(parts)
        except ValueError:
            return None


def is_safe_command(command: str, repo_root: str | Path = ".") -> bool:
    """Quick check if a command is safe.

    Args:
        command: Shell command
        repo_root: Repository root

    Returns:
        True if safe
    """
    guard = SafetyGuard(repo_root=repo_root, allow_shell=True)
    return guard.check_command(command).allowed


def is_safe_path(path: str | Path, repo_root: str | Path = ".") -> bool:
    """Quick check if a path is safe.

    Args:
        path: File path
        repo_root: Repository root

    Returns:
        True if safe
    """
    guard = SafetyGuard(repo_root=repo_root)
    return guard.check_path(path).allowed


__all__ = [
    "SafetyGuard",
    "SafetyCheck",
    "is_safe_command",
    "is_safe_path",
    "DENYLIST_COMMANDS",
    "ALLOWLIST_TEST_COMMANDS",
]
