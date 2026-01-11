"""Fuzzy patch application using google-diff-match-patch."""

from __future__ import annotations

from dataclasses import dataclass

from diff_match_patch import diff_match_patch


@dataclass
class PatchResult:
    text: str
    applied: bool
    details: tuple[bool, ...]


def apply_fuzzy_patch(original: str, modified: str, target: str) -> PatchResult:
    """Apply `original -> modified` transform to `target` using fuzzy matching."""

    dmp = diff_match_patch()
    patches = dmp.patch_make(original, modified)
    new_text, results = dmp.patch_apply(patches, target)
    applied = all(results)
    return PatchResult(text=new_text, applied=applied, details=tuple(results))


__all__ = ["PatchResult", "apply_fuzzy_patch"]
