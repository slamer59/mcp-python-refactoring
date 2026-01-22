"""Scope resolution for RefactorOps analysis."""

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Dict, List, Optional, Sequence, Set

from .exec import run_command
from .schema import ScopeGit, ScopeSpec


DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
    "vendor",
}

DEFAULT_EXCLUDED_EXTENSIONS: Set[str] = {
    ".bin",
    ".bmp",
    ".class",
    ".dll",
    ".dmg",
    ".egg",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".iso",
    ".jar",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".pyc",
    ".pyo",
    ".rar",
    ".so",
    ".tar",
    ".tif",
    ".tiff",
    ".tgz",
    ".whl",
    ".zip",
    ".7z",
}


@dataclass
class ResolvedScope:
    files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    skipped: List[Dict[str, str]] = field(default_factory=list)


def resolve_scope(
    repo_root: str,
    scope: ScopeSpec,
    fallback_paths: Optional[Sequence[str]] = None,
    git_timeout_sec: int = 10,
    excluded_dirs: Optional[Set[str]] = None,
    excluded_extensions: Optional[Set[str]] = None,
) -> ResolvedScope:
    """Resolve file scope for analysis."""

    root = Path(repo_root).resolve()
    result = ResolvedScope()
    excluded_dirs = excluded_dirs or DEFAULT_EXCLUDED_DIRS
    excluded_extensions = excluded_extensions or DEFAULT_EXCLUDED_EXTENSIONS

    if scope.type == "repo":
        files = _collect_repo_files(root, result, excluded_dirs, excluded_extensions)
    elif scope.type == "paths":
        files = _collect_paths_files(root, scope.paths, result, excluded_dirs, excluded_extensions)
    elif scope.type == "changed":
        files = _collect_changed_files(
            root,
            scope.git,
            scope.paths,
            fallback_paths,
            result,
            git_timeout_sec,
            excluded_dirs,
            excluded_extensions,
        )
    else:
        _add_error(result, "unsupported_scope_type")
        files = []

    result.files = sorted(set(files))
    if not result.files:
        _add_error(result, "no_files_matched")

    return result


def _collect_repo_files(
    root: Path,
    result: ResolvedScope,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
) -> List[str]:
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in excluded_dirs and not os.path.islink(os.path.join(dirpath, name))
        ]
        for name in filenames:
            path = Path(dirpath) / name
            _maybe_add_file(path, root, result, excluded_dirs, excluded_extensions, files)
    return files


def _collect_paths_files(
    root: Path,
    paths: Sequence[str],
    result: ResolvedScope,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
) -> List[str]:
    files: List[str] = []
    for raw_path in paths:
        candidate = _resolve_candidate_path(root, raw_path, result)
        if candidate is None:
            continue
        if candidate.is_dir():
            for dirpath, dirnames, filenames in os.walk(candidate):
                dirnames[:] = [
                    name
                    for name in dirnames
                    if name not in excluded_dirs
                    and not os.path.islink(os.path.join(dirpath, name))
                ]
                for name in filenames:
                    path = Path(dirpath) / name
                    _maybe_add_file(path, root, result, excluded_dirs, excluded_extensions, files)
        elif candidate.is_file():
            _maybe_add_file(candidate, root, result, excluded_dirs, excluded_extensions, files)
        else:
            _add_skipped(result, candidate, "path_not_found")
            _add_error(result, "path_not_found")
    return files


def _collect_changed_files(
    root: Path,
    git_spec: Optional[ScopeGit],
    scope_paths: Sequence[str],
    fallback_paths: Optional[Sequence[str]],
    result: ResolvedScope,
    git_timeout_sec: int,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
) -> List[str]:
    if git_spec is None:
        _add_error(result, "git_range_missing")
        return _collect_paths_files(
            root,
            fallback_paths or scope_paths,
            result,
            excluded_dirs,
            excluded_extensions,
        )

    git_result = run_command(
        ["git", "diff", "--name-only", f"{git_spec.base}...{git_spec.head}"],
        repo_root=str(root),
        timeout_sec=git_timeout_sec,
    )

    if not git_result.ok or git_result.exit_code != 0:
        _add_error(result, "git_diff_failed")
        return _collect_paths_files(
            root,
            fallback_paths or scope_paths,
            result,
            excluded_dirs,
            excluded_extensions,
        )

    changed_paths = [line.strip() for line in git_result.stdout.splitlines() if line.strip()]
    return _collect_paths_files(root, changed_paths, result, excluded_dirs, excluded_extensions)


def _resolve_candidate_path(root: Path, raw_path: str, result: ResolvedScope) -> Optional[Path]:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        _add_error(result, "path_resolution_failed")
        return None

    if not _is_within_repo(resolved, root):
        _add_error(result, "path_outside_repo")
        _add_skipped(result, resolved, "path_outside_repo")
        return None

    return resolved


def _maybe_add_file(
    path: Path,
    root: Path,
    result: ResolvedScope,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
    files: List[str],
) -> None:
    if not path.exists():
        _add_skipped(result, path, "path_not_found")
        return

    resolved = path.resolve()
    if not _is_within_repo(resolved, root):
        _add_error(result, "path_outside_repo")
        _add_skipped(result, resolved, "path_outside_repo")
        return

    if resolved.is_symlink():
        _add_skipped(result, resolved, "symlink")
        return

    if _has_excluded_dir(resolved, excluded_dirs):
        _add_skipped(result, resolved, "excluded_dir")
        return

    if resolved.suffix.lower() in excluded_extensions:
        _add_skipped(result, resolved, "excluded_extension")
        return

    if _is_binary_file(resolved):
        _add_skipped(result, resolved, "binary_file")
        return

    files.append(resolved.relative_to(root).as_posix())


def _has_excluded_dir(path: Path, excluded_dirs: Set[str]) -> bool:
    return any(part in excluded_dirs for part in path.parts)


def _is_within_repo(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(1024)
    except OSError:
        return True
    return b"\x00" in chunk


def _add_error(result: ResolvedScope, code: str) -> None:
    if code not in result.errors:
        result.errors.append(code)


def _add_skipped(result: ResolvedScope, path: Path, reason: str) -> None:
    result.skipped.append({"path": path.as_posix(), "reason": reason})
