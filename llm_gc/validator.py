"""LLM-based code validation.

Validates generated code before applying changes.
Based on patterns from quotient-ai/judges and LangGraph reflection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal, Callable, Awaitable

from pydantic import BaseModel

from llm_gc.config import ModelConfig, MinionConfigs, get_validator_config


class ValidationResult(BaseModel):
    """Result of validation check."""
    passed: bool
    reason: Optional[str] = None
    check_type: Literal["syntax", "task", "preservation", "all"] = "all"


VALIDATOR_PROMPT = """You are a code validator. Check if the modified code is correct.

Original file:
```{lang}
{original}
```

Modified file:
```{lang}
{modified}
```

Task requested: {task}

Check:
1. SYNTAX: Does the modified code have valid syntax?
2. TASK: Did it complete the requested task ({task})?
3. PRESERVATION: Is all original logic preserved exactly (no accidental changes)?

Respond with exactly one line:
PASS - if all checks pass
FAIL: <reason> - if any check fails

Examples:
PASS
FAIL: Syntax error on line 42
FAIL: Did not add docstrings to function bar()
FAIL: Logic changed - removed error handling in try block"""


RETRY_PROMPT = """Your previous output had an error:
{error}

Original file:
```{lang}
{original}
```

Your output (with error):
```{lang}
{generated}
```

Fix the issue and output ONLY the corrected complete file in a code block.
Do NOT explain what you did. Just output the fixed code."""


@dataclass
class CodeValidator:
    """LLM-based code validator."""
    client: object  # OllamaClient
    config: ModelConfig

    async def validate(
        self,
        original: str,
        modified: str,
        task: str,
        lang: str = "python"
    ) -> ValidationResult:
        """Validate that modified code is correct.

        Args:
            original: Original source code
            modified: Modified source code
            task: Task that was requested
            lang: Language for code blocks

        Returns:
            ValidationResult with passed/failed and reason.
        """
        prompt = VALIDATOR_PROMPT.format(
            original=original,
            modified=modified,
            task=task,
            lang=lang,
        )

        response, _ = await self.client.prompt(prompt, self.config, role="validator")
        return self._parse_response(response)

    def _parse_response(self, response: str) -> ValidationResult:
        """Parse PASS/FAIL response from validator."""
        response = response.strip()

        # Handle multi-line responses - take first line
        first_line = response.split("\n")[0].strip()

        if first_line.upper().startswith("PASS"):
            return ValidationResult(passed=True)
        elif first_line.upper().startswith("FAIL"):
            # Extract reason after "FAIL:" or "FAIL -"
            reason = first_line
            for prefix in ["FAIL:", "FAIL -", "FAIL"]:
                if first_line.upper().startswith(prefix):
                    reason = first_line[len(prefix):].strip()
                    break
            return ValidationResult(passed=False, reason=reason or "Validation failed")
        else:
            # Unexpected response format
            return ValidationResult(
                passed=False,
                reason=f"Invalid validator response: {first_line[:100]}"
            )


@dataclass
class GenerateValidateLoop:
    """Generate → Validate → Retry loop."""
    generator: Callable[[str, str], Awaitable[str]]  # (original, task) -> generated
    generator_retry: Callable[[str, str, str], Awaitable[str]]  # (original, generated, error) -> fixed
    validator: CodeValidator
    max_retries: int = 1
    notify_on_fail: bool = True

    async def run(
        self,
        original: str,
        task: str,
        lang: str = "python"
    ) -> dict:
        """Run generate → validate → retry loop.

        Args:
            original: Original source code
            task: Task to perform
            lang: Language for code blocks

        Returns:
            dict with status, output, attempts, and error info.
        """
        attempt = 0
        last_error: Optional[str] = None
        generated: Optional[str] = None

        while attempt <= self.max_retries:
            # Generate
            if attempt == 0:
                generated = await self.generator(original, task)
            else:
                # Retry with error feedback
                generated = await self.generator_retry(original, generated, last_error)

            # Validate
            result = await self.validator.validate(original, generated, task, lang)

            if result.passed:
                return {
                    "status": "success",
                    "output": generated,
                    "attempts": attempt + 1,
                }

            last_error = result.reason
            attempt += 1

        # All retries failed
        return {
            "status": "failed",
            "output": generated,
            "attempts": attempt,
            "last_error": last_error,
            "suggestion": "Manual review required - minion unable to complete task",
        }


def create_validator(client, configs: MinionConfigs) -> CodeValidator:
    """Create a CodeValidator from configs.

    Args:
        client: OllamaClient instance
        configs: MinionConfigs with validator settings

    Returns:
        Configured CodeValidator.
    """
    validator_config = get_validator_config(configs)
    return CodeValidator(client=client, config=validator_config)


def create_retry_prompt(original: str, generated: str, error: str, lang: str = "python") -> str:
    """Create prompt for retry with error feedback.

    Args:
        original: Original source code
        generated: Generated code with error
        error: Error message from validator
        lang: Language for code blocks

    Returns:
        Retry prompt string.
    """
    return RETRY_PROMPT.format(
        original=original,
        generated=generated,
        error=error,
        lang=lang,
    )
