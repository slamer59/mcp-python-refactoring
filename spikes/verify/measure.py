"""Measure how many functions changed in a repo's history `verify` could actually check.

usage: python measure.py <repo> [max_commits]
Static heuristic: classifies each changed function by why it would or wouldn't be checkable.
"""
import ast
import subprocess
import sys
from collections import Counter

IO_NAMES = {"open", "input", "exec", "eval", "__import__"}
IO_ATTRS = {
    "subprocess", "system", "popen", "remove", "unlink", "rmdir", "makedirs", "mkdir", "rename",
    "write_text", "write_bytes", "read_text", "read_bytes", "touch", "rmtree", 
    "copyfile", "connect", "execute", "request", "post", "urlopen", "socket",
    "Popen", "check_output", "glob", "rglob", "walk", "listdir", "scandir", "exists",
    "is_file", "is_dir", "getcwd", "chdir", "environ", "getenv", "mkdtemp",
    "NamedTemporaryFile", "TemporaryDirectory", "sleep", "kill", "Progress", "ask", "confirm",
}
NONDET_ATTRS = {"time", "perf_counter", "now", "today", "utcnow", "random", "randint", "choice",
                "shuffle", "uuid4", "urandom", "monotonic"}


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    return r.stdout.decode(errors="replace") if r.returncode == 0 else None


def collect(source):
    """qualname -> (node, class_name|None)"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out = {}

    def visit(body, prefix, cls):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[prefix + n.name] = (n, cls)
            elif isinstance(n, ast.ClassDef):
                visit(n.body, prefix + n.name + ".", n.name)
    visit(tree.body, "", None)
    return out


def direct_flags(node):
    io = nondet = False
    calls = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name):
                calls.add(f.id)
                io |= f.id in IO_NAMES
            elif isinstance(f, ast.Attribute):
                io |= f.attr in IO_ATTRS
                nondet |= f.attr in NONDET_ATTRS
                if isinstance(f.value, ast.Name) and f.value.id == "self":
                    calls.add(f.attr)
        elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            io |= sub.value.id in {"subprocess", "socket", "requests", "httpx", "duckdb", "sqlite3", "shutil"}
            nondet |= sub.value.id in {"random", "time", "uuid"}
    return io, nondet, calls


def classify(name, old, new, module_funcs):
    old_node, _ = old
    node, cls = new
    if ast.dump(old_node.args) != ast.dump(node.args):
        return "signature changed"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async"
    io, nondet, calls = direct_flags(node)
    # one level of transitive I/O through same-module functions / methods
    for c in calls:
        for qual, (other, _) in module_funcs.items():
            if qual.split(".")[-1] == c and other is not node:
                o_io, o_nd, _ = direct_flags(other)
                io |= o_io
                nondet |= o_nd
    if io:
        return "does I/O"
    if nondet:
        return "nondeterministic"
    is_static = any(isinstance(d, ast.Name) and d.id in {"staticmethod", "classmethod"} for d in node.decorator_list)
    if cls and not is_static:
        return "method (needs instance)"
    return "CHECKABLE"


def main():
    repo = sys.argv[1]
    limit = sys.argv[2] if len(sys.argv) > 2 else "200"
    commits = git(repo, "log", "--no-merges", f"-n{limit}", "--format=%H %s", "--", "*.py").splitlines()
    totals, refactor_totals = Counter(), Counter()
    hints = Counter()
    for line in commits:
        sha, subject = line.split(" ", 1)
        is_refactor = any(w in subject.lower() for w in ("refactor", "simplif", "clean", "extract", "rename"))
        files = (git(repo, "diff", "--name-only", f"{sha}^", sha, "--", "*.py") or "").split()
        for f in files:
            old_src, new_src = git(repo, "show", f"{sha}^:{f}"), git(repo, "show", f"{sha}:{f}")
            old, new = collect(old_src or ""), collect(new_src or "")
            for q in old.keys() | new.keys():
                if q not in old:
                    kind = "added"
                elif q not in new:
                    kind = "removed"
                elif ast.dump(old[q][0]) == ast.dump(new[q][0]):
                    continue
                else:
                    kind = classify(q, old[q], new[q], new)
                    if kind == "CHECKABLE":
                        a = new[q][0].args
                        params = [p for p in a.posonlyargs + a.args + a.kwonlyargs if p.arg not in ("self", "cls")]
                        hints["fully type-hinted" if all(p.annotation for p in params) else "missing hints"] += 1
                totals[kind] += 1
                if is_refactor:
                    refactor_totals[kind] += 1

    def show(title, c):
        modified = sum(v for k, v in c.items() if k not in ("added", "removed"))
        print(f"\n{title}  (modified functions: {modified}, plus {c['added']} added / {c['removed']} removed)")
        for k, v in c.most_common():
            if k in ("added", "removed"):
                continue
            print(f"  {k:<26} {v:>5}  {100 * v / modified:5.1f}%")

    print(f"repo: {repo}   commits touching .py: {len(commits)}")
    show("ALL COMMITS", totals)
    if refactor_totals:
        show("REFACTOR-LIKE COMMITS (subject mentions refactor/simplify/clean/extract/rename)", refactor_totals)
    print(f"\ncheckable functions with type hints: {dict(hints)}")


if __name__ == "__main__":
    main()
