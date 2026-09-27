"""
Git diff ingestion layer.

Reads the diff between two branches/commits using GitPython and
populates a RepoContext object.  All file I/O stays local.
"""
from __future__ import annotations

from pathlib import Path

import git

from pr_sentinel.models import FileDiff, RepoContext

# Max bytes to load for a single file's full source (safety cap)
_MAX_FILE_BYTES = 200_000

# Source file extensions worth loading for cross-file analysis
_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".kt",
    ".yaml", ".yml", ".toml", ".json", ".env", ".cfg", ".ini",
}


def _read_file_safe(path: Path) -> str | None:
    """Read a text file, returning None on any error or size overrun."""
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def load_repo_context(
    repo_path: str,
    base_ref: str = "main",
    head_ref: str = "HEAD",
    pr_title: str = "",
    pr_description: str = "",
    load_full_contents: bool = True,
    cross_file_context: bool = True,
) -> RepoContext:
    """
    Build a RepoContext from a local git repository.

    Parameters
    ----------
    repo_path:
        Absolute or relative path to the git repo root.
    base_ref:
        The base branch/commit to diff against (e.g. ``"main"``).
    head_ref:
        The head branch/commit being reviewed (default ``"HEAD"``).
    pr_title / pr_description:
        Optional metadata surfaced in reports and agent prompts.
    load_full_contents:
        If True, read the full current source for every changed file.
    cross_file_context:
        If True (and load_full_contents is True), also load source for
        files that *import* or are in the same package as a changed file,
        so ConsistencyAgent can reason about callers and dependencies
        without the agent needing to request them explicitly.
    """
    repo = git.Repo(repo_path, search_parent_directories=True)
    resolved_root = Path(repo.working_tree_dir or repo_path)

    base_commit = repo.commit(base_ref)
    head_commit = repo.commit(head_ref)

    diff_index = base_commit.diff(head_commit, create_patch=True)

    files_changed: list[FileDiff] = []
    for diff_item in diff_index:
        patch_text = ""
        try:
            patch_bytes = diff_item.diff
            if isinstance(patch_bytes, bytes):
                patch_text = patch_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

        lines = patch_text.splitlines()
        additions = sum(1 for ln in lines if ln.startswith("+") and not ln.startswith("+++"))
        deletions = sum(1 for ln in lines if ln.startswith("-") and not ln.startswith("---"))

        files_changed.append(
            FileDiff(
                path=diff_item.b_path or diff_item.a_path or "",
                old_path=diff_item.a_path if diff_item.renamed_file else None,
                additions=additions,
                deletions=deletions,
                patch=patch_text,
            )
        )

    full_contents: dict[str, str] = {}

    if load_full_contents:
        # 1. Always load the changed files themselves
        for fd in files_changed:
            abs_path = resolved_root / fd.path
            content = _read_file_safe(abs_path)
            if content is not None:
                full_contents[fd.path] = content

        # 2. Cross-file context: load sibling files in the same directories
        #    as the changed files so agents can reason about callers/dependencies.
        if cross_file_context:
            changed_dirs = {Path(fd.path).parent for fd in files_changed}
            for directory in changed_dirs:
                abs_dir = resolved_root / directory
                if not abs_dir.is_dir():
                    continue
                for sibling in abs_dir.iterdir():
                    rel = str(sibling.relative_to(resolved_root)).replace("\\", "/")
                    if rel in full_contents:
                        continue  # already loaded
                    if sibling.suffix.lower() not in _SOURCE_EXTENSIONS:
                        continue
                    content = _read_file_safe(sibling)
                    if content is not None:
                        full_contents[rel] = content

    # Attempt to detect head branch name
    head_branch = head_ref
    try:
        head_branch = repo.active_branch.name
    except TypeError:
        pass  # detached HEAD — keep head_ref as-is

    return RepoContext(
        repo_path=str(resolved_root),
        base_branch=base_ref,
        head_branch=head_branch,
        pr_title=pr_title,
        pr_description=pr_description,
        files_changed=files_changed,
        full_file_contents=full_contents,
    )
