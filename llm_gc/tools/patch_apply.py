"""Autonomous patch application for minions.

Applies patches directly without user confirmation.
Uses multiple strategies for robustness.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from llm_gc.metrics import log_metric
from llm_gc.patcher import apply_patch_robust, PatchAttempt


@dataclass
class ApplyResult:
    """Result of applying a patch."""

    success: bool
    file_path: str
    strategy: str
    original_content: str | None = None
    new_content: str | None = None
    error: str | None = None
    backup_path: str | None = None


@dataclass
class PatchApplier:
    """Autonomous patch applier with safety constraints."""

    repo_root: Path
    create_backups: bool = True
    backup_dir: Path | None = None

    def __post_init__(self):
        self.repo_root = Path(self.repo_root).resolve()
        if self.backup_dir is None:
            self.backup_dir = self.repo_root / ".minion-backups"

    def _is_safe_path(self, file_path: Path) -> bool:
        """Check if path is within repo root (path sandboxing)."""
        try:
            resolved = file_path.resolve()
            return str(resolved).startswith(str(self.repo_root))
        except (OSError, ValueError):
            return False

    def _create_backup(self, file_path: Path) -> str | None:
        """Create a backup of the file before modifying."""
        if not self.create_backups:
            return None

        if not file_path.exists():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Create unique backup name
        import time
        timestamp = int(time.time() * 1000)
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        backup_path.write_text(file_path.read_text())
        return str(backup_path)

    def apply_search_replace(
        self,
        file_path: str | Path,
        search: str,
        replace: str,
    ) -> ApplyResult:
        """Apply a search/replace patch to a file.

        Args:
            file_path: Path to file (relative to repo_root or absolute)
            search: Text to find
            replace: Text to replace with

        Returns:
            ApplyResult with status
        """
        start_time = time.time()
        # Resolve path
        path = Path(file_path)
        if not path.is_absolute():
            path = self.repo_root / path
        path = path.resolve()

        # Safety check
        if not self._is_safe_path(path):
            return ApplyResult(
                success=False,
                file_path=str(file_path),
                strategy="none",
                error=f"Path outside repo root: {path}",
            )

        if not path.exists():
            return ApplyResult(
                success=False,
                file_path=str(file_path),
                strategy="none",
                error=f"File not found: {path}",
            )

        # Read original
        try:
            original = path.read_text()
        except Exception as e:
            return ApplyResult(
                success=False,
                file_path=str(file_path),
                strategy="none",
                error=f"Failed to read file: {e}",
            )

        # Create backup
        backup_path = self._create_backup(path)

        # Apply patch using robust strategies
        attempt: PatchAttempt = apply_patch_robust(original, search, replace, str(path))

        if not attempt.success:
            return ApplyResult(
                success=False,
                file_path=str(file_path),
                strategy=attempt.strategy,
                original_content=original,
                error=attempt.error or "Patch did not match",
                backup_path=backup_path,
            )

        # Write result
        try:
            path.write_text(attempt.result)
        except Exception as e:
            return ApplyResult(
                success=False,
                file_path=str(file_path),
                strategy=attempt.strategy,
                original_content=original,
                error=f"Failed to write file: {e}",
                backup_path=backup_path,
            )

        duration_ms = int((time.time() - start_time) * 1000)
        log_metric(
            task_type="apply",
            task_description=f"Apply patch: {file_path}",
            duration_ms=duration_ms,
            success=True,
            patch_applied=True,
        )
        return ApplyResult(
            success=True,
            file_path=str(file_path),
            strategy=attempt.strategy,
            original_content=original,
            new_content=attempt.result,
            backup_path=backup_path,
        )

    def apply_unified_diff(self, diff: str) -> list[ApplyResult]:
        """Apply a unified diff to the repo.

        Args:
            diff: Unified diff content

        Returns:
            List of ApplyResult for each file
        """
        results = []

        # Try git apply first
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".patch", delete=False
            ) as f:
                f.write(diff)
                patch_file = f.name

            proc = subprocess.run(
                ["git", "apply", "--check", patch_file],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )

            if proc.returncode == 0:
                # Dry run passed, apply for real
                proc = subprocess.run(
                    ["git", "apply", patch_file],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                )

                if proc.returncode == 0:
                    # Parse files from diff header
                    import re
                    files = re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)
                    for file_path in files:
                        results.append(ApplyResult(
                            success=True,
                            file_path=file_path,
                            strategy="git_apply",
                        ))
                    return results

        except FileNotFoundError:
            pass  # git not available
        except Exception:
            pass

        # Fall back to manual parsing
        results.append(ApplyResult(
            success=False,
            file_path="<unified-diff>",
            strategy="git_apply",
            error="git apply failed, manual parsing not yet implemented",
        ))

        return results

    def rollback(self, backup_path: str) -> bool:
        """Rollback a file from its backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if rollback succeeded
        """
        backup = Path(backup_path)
        if not backup.exists():
            return False

        # Extract original filename (remove timestamp and .bak)
        import re
        match = re.match(r"(.+)\.\d+\.bak$", backup.name)
        if not match:
            return False

        original_name = match.group(1)

        # Find the original file in repo
        # This is a simple heuristic - may need improvement
        for path in self.repo_root.rglob(original_name):
            if self._is_safe_path(path):
                path.write_text(backup.read_text())
                return True

        return False


def apply_patch(
    file_path: str | Path,
    search: str,
    replace: str,
    repo_root: str | Path = ".",
) -> ApplyResult:
    """Convenience function to apply a search/replace patch.

    Args:
        file_path: Path to file
        search: Text to find
        replace: Text to replace with
        repo_root: Repository root

    Returns:
        ApplyResult with status
    """
    applier = PatchApplier(repo_root=repo_root)
    return applier.apply_search_replace(file_path, search, replace)


def apply_diff(
    diff: str,
    repo_root: str | Path = ".",
) -> list[ApplyResult]:
    """Convenience function to apply a unified diff.

    Args:
        diff: Unified diff content
        repo_root: Repository root

    Returns:
        List of ApplyResult
    """
    applier = PatchApplier(repo_root=repo_root)
    return applier.apply_unified_diff(diff)


__all__ = ["PatchApplier", "ApplyResult", "apply_patch", "apply_diff"]
