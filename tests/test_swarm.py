"""Tests for swarm.py - parallel minion execution."""

from unittest.mock import MagicMock, patch

from llm_gc.swarm import (
    MinionTask,
    Swarm,
    run_minion_task,
    simplify_prompt,
    swarm_dispatch,
)

# ─────────────────────────────────────────────────────────────
# MinionTask Tests
# ─────────────────────────────────────────────────────────────


class TestMinionTask:
    """Test MinionTask dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        task = MinionTask(description="Test task")
        assert task.kind == "chat"
        assert task.target is None
        assert task.context_files == []
        assert task.repo_root == "."
        assert task.rounds == 2
        assert task.retries == 0
        assert task.max_retries == 2
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None

    def test_patch_task(self):
        """Test creating a patch task."""
        task = MinionTask(
            description="Add docstring",
            kind="patch",
            target="src/utils.py",
            context_files=["src/main.py"],
        )
        assert task.kind == "patch"
        assert task.target == "src/utils.py"
        assert task.context_files == ["src/main.py"]


# ─────────────────────────────────────────────────────────────
# Prompt Simplification Tests
# ─────────────────────────────────────────────────────────────


class TestSimplifyPrompt:
    """Test prompt simplification for retries."""

    def test_first_attempt_unchanged(self):
        """First attempt (retry=0) should not change prompt."""
        prompt = "Please add a docstring to this function."
        assert simplify_prompt(prompt, 0) == prompt

    def test_retry_1_strips_verbose(self):
        """Retry 1 should strip verbose language."""
        prompt = "Please add a docstring to this function."
        result = simplify_prompt(prompt, 1)
        assert "Please " not in result
        assert "SIMPLE TASK" in result
        assert "OUTPUT ONLY THE RESULT" in result

    def test_retry_1_strips_could_you(self):
        """Retry 1 should strip 'Could you' phrases."""
        prompt = "Could you fix this bug in the parser?"
        result = simplify_prompt(prompt, 1)
        assert "Could you " not in result

    def test_retry_2_ultra_simple(self):
        """Retry 2+ should truncate to first 20 words."""
        prompt = " ".join([f"word{i}" for i in range(50)])
        result = simplify_prompt(prompt, 2)
        assert result.startswith("DO THIS:")
        assert result.endswith("...")
        # Should have at most 20 words from original
        words_in_result = result.replace("DO THIS:", "").replace("...", "").split()
        assert len(words_in_result) <= 20


# ─────────────────────────────────────────────────────────────
# Swarm Initialization Tests
# ─────────────────────────────────────────────────────────────


class TestSwarmInit:
    """Test Swarm class initialization."""

    def test_default_values(self):
        """Test default Swarm values."""
        swarm = Swarm()
        assert swarm.workers == 5
        assert swarm.max_retries == 2
        assert swarm.rounds == 2
        assert swarm.repo_root == "."
        assert swarm.tasks == []
        assert swarm.completed == []
        assert swarm.failed == []

    def test_custom_values(self):
        """Test Swarm with custom values."""
        swarm = Swarm(workers=10, max_retries=3, rounds=4, repo_root="/tmp")
        assert swarm.workers == 10
        assert swarm.max_retries == 3
        assert swarm.rounds == 4
        assert swarm.repo_root == "/tmp"


# ─────────────────────────────────────────────────────────────
# Swarm Task Addition Tests
# ─────────────────────────────────────────────────────────────


class TestSwarmAddTasks:
    """Test adding tasks to Swarm."""

    def test_add_chat(self):
        """Test adding a chat task."""
        swarm = Swarm()
        swarm.add_chat("Review this code", context_files=["src/main.py"])

        assert len(swarm.tasks) == 1
        task = swarm.tasks[0]
        assert task.description == "Review this code"
        assert task.kind == "chat"
        assert task.context_files == ["src/main.py"]

    def test_add_patch(self):
        """Test adding a patch task."""
        swarm = Swarm()
        swarm.add_patch(
            description="Add docstring",
            target="src/utils.py",
            context_files=["src/types.py"],
        )

        assert len(swarm.tasks) == 1
        task = swarm.tasks[0]
        assert task.description == "Add docstring"
        assert task.kind == "patch"
        assert task.target == "src/utils.py"
        assert task.context_files == ["src/types.py"]

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks."""
        swarm = Swarm()
        swarm.add_chat("Review code")
        swarm.add_patch("Fix bug", target="bug.py")
        swarm.add_chat("Explain function")

        assert len(swarm.tasks) == 3
        assert swarm.tasks[0].kind == "chat"
        assert swarm.tasks[1].kind == "patch"
        assert swarm.tasks[2].kind == "chat"


# ─────────────────────────────────────────────────────────────
# Run Minion Task Tests
# ─────────────────────────────────────────────────────────────


class TestRunMinionTask:
    """Test individual task execution."""

    def test_chat_task_success(self):
        """Test successful chat task execution."""
        task = MinionTask(description="Test task")

        with patch("llm_gc.swarm.run_chat") as mock_chat:
            mock_chat.return_value = {"summary": "Test result"}
            result = run_minion_task(task)

        assert result.status == "completed"
        assert result.result == "Test result"
        assert result.error is None

    def test_patch_task_success(self):
        """Test successful patch task execution."""
        task = MinionTask(
            description="Add docstring",
            kind="patch",
            target="test.py",
        )

        with patch("llm_gc.swarm.run_patch") as mock_patch:
            mock_patch.return_value = {"patch_path": "/tmp/test.patch"}
            result = run_minion_task(task)

        assert result.status == "completed"
        assert result.result == "/tmp/test.patch"

    def test_patch_task_empty(self):
        """Test patch task with empty result."""
        task = MinionTask(
            description="Add docstring",
            kind="patch",
            target="test.py",
        )

        with patch("llm_gc.swarm.run_patch") as mock_patch:
            mock_patch.return_value = {}
            result = run_minion_task(task)

        assert result.status == "empty"
        assert result.result == ""

    def test_task_failure(self):
        """Test task that throws exception."""
        task = MinionTask(description="Failing task")

        with patch("llm_gc.swarm.run_chat") as mock_chat:
            mock_chat.side_effect = Exception("Connection refused")
            result = run_minion_task(task)

        assert result.status == "failed"
        assert "Connection refused" in result.error


# ─────────────────────────────────────────────────────────────
# Swarm Dispatch Tests
# ─────────────────────────────────────────────────────────────


class TestSwarmDispatch:
    """Test the convenience swarm_dispatch function."""

    def test_dispatch_creates_correct_tasks(self):
        """Test that dispatch creates correct task types."""
        tasks = [
            {"description": "Review code"},
            {"description": "Fix bug", "kind": "patch", "target": "bug.py"},
        ]

        with patch.object(Swarm, "run") as mock_run:
            mock_run.return_value = {"completed": [], "failed": [], "stats": {}}
            swarm_dispatch(tasks, workers=2)

        # Verify run was called
        mock_run.assert_called_once()

    def test_dispatch_with_context_files(self):
        """Test dispatch with context files."""
        tasks = [
            {
                "description": "Review auth",
                "context_files": ["auth.py", "users.py"],
            },
        ]

        with patch.object(Swarm, "run") as mock_run:
            mock_run.return_value = {"completed": [], "failed": [], "stats": {}}
            swarm_dispatch(tasks)

        mock_run.assert_called_once()


# ─────────────────────────────────────────────────────────────
# Integration-style Tests (with mocked orchestrator)
# ─────────────────────────────────────────────────────────────


class TestSwarmRun:
    """Test Swarm.run() with mocked workers."""

    def test_run_logs_progress(self):
        """Test that run() calls progress callback."""
        swarm = Swarm(workers=1)
        swarm.add_chat("Test task")

        progress_messages = []

        # Mock the entire ProcessPoolExecutor context
        with patch("llm_gc.swarm.ProcessPoolExecutor") as mock_executor_class:
            # Create mock future
            mock_future = MagicMock()
            mock_future.result.return_value = {
                "description": "Test task",
                "kind": "chat",
                "target": None,
                "context_files": [],
                "repo_root": ".",
                "rounds": 2,
                "retries": 0,
                "max_retries": 2,
                "status": "completed",
                "result": "Done",
                "error": None,
            }

            # Make as_completed return our mock future
            mock_executor = MagicMock()
            mock_executor.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor.__exit__ = MagicMock(return_value=False)
            mock_executor.submit.return_value = mock_future
            mock_executor_class.return_value = mock_executor

            with patch("llm_gc.swarm.as_completed", return_value=[mock_future]):
                with patch("llm_gc.swarm.add_bananas", return_value=1):
                    with patch("llm_gc.swarm.celebrate", return_value=""):
                        with patch("llm_gc.swarm.get_bananas", return_value=1):
                            result = swarm.run(on_progress=progress_messages.append)

        assert result["stats"]["completed"] == 1
        assert any("Swarm starting" in msg for msg in progress_messages)

    def test_stats_returned(self):
        """Test that run returns proper stats."""
        swarm = Swarm(workers=1)
        swarm.add_chat("Task 1")
        swarm.add_chat("Task 2")

        with patch("llm_gc.swarm.ProcessPoolExecutor") as mock_executor_class:
            mock_future = MagicMock()
            mock_future.result.return_value = {
                "description": "Task",
                "kind": "chat",
                "target": None,
                "context_files": [],
                "repo_root": ".",
                "rounds": 2,
                "retries": 0,
                "max_retries": 2,
                "status": "completed",
                "result": "Done",
                "error": None,
            }

            mock_executor = MagicMock()
            mock_executor.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor.__exit__ = MagicMock(return_value=False)
            mock_executor.submit.return_value = mock_future
            mock_executor_class.return_value = mock_executor

            with patch("llm_gc.swarm.as_completed", return_value=[mock_future, mock_future]):
                with patch("llm_gc.swarm.add_bananas", return_value=2):
                    with patch("llm_gc.swarm.celebrate", return_value=""):
                        with patch("llm_gc.swarm.get_bananas", return_value=2):
                            result = swarm.run()

        assert "completed" in result
        assert "failed" in result
        assert "stats" in result
        assert result["stats"]["total"] == 2
