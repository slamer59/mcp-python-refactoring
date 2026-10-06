"""Spike: behaviour-equivalence check for refactors (old vs new on the same inputs).

usage: python spike.py <repo> <base_ref> <random|symbolic> [max_examples] [function]
"""
import ast
import copy
import importlib.util
import inspect
import math
import pickle
import subprocess
import sys
import tarfile
import io
import tempfile
import time
import typing
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st

WORKER = r'''
import sys, pickle, importlib, io, contextlib
sys.path.insert(0, sys.argv[1])
mod = importlib.import_module(sys.argv[2])
inp, out = sys.stdin.buffer, sys.stdout.buffer
while True:
    hdr = inp.read(8)
    if not hdr:
        break
    fname, args = pickle.loads(inp.read(int.from_bytes(hdr, "big")))
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            res = ("return", getattr(mod, fname)(*args), args, buf.getvalue())
    except Exception as e:
        res = ("raise", type(e).__name__, args, buf.getvalue())
    data = pickle.dumps(res)
    out.write(len(data).to_bytes(8, "big") + data)
    out.flush()
'''


# ---------- changes + snapshot ----------
def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True).stdout


def functions(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    return {n.name: ast.unparse(n) for n in tree.body if isinstance(n, (ast.FunctionDef,))}


def changed_functions(repo: str, base: str):
    files = git(repo, "diff", "--name-only", base, "--", "*.py").decode().split()
    out = []
    for f in files:
        old = functions(git(repo, "show", f"{base}:{f}").decode())
        new = functions(Path(repo, f).read_text())
        for name in old.keys() & new.keys():
            if old[name] != new[name]:
                out.append((f, name))
    return out


def snapshot(repo: str, base: str) -> str:
    dest = tempfile.mkdtemp(prefix="verify-base-")
    tarfile.open(fileobj=io.BytesIO(git(repo, "archive", base))).extractall(dest, filter="data")
    return dest


# ---------- strategies + comparison ----------
def strategy_for(fn):
    hints = typing.get_type_hints(fn)
    params = [p for p in inspect.signature(fn).parameters]
    return st.tuples(*(st.from_type(hints[p]) for p in params))


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return (math.isnan(a) and math.isnan(b)) or math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def explain(old, new):
    for label, i in (("outcome", 0), ("value", 1), ("arguments after call", 2), ("stdout", 3)):
        if not same(old[i], new[i]):
            return f"{label}: old={old[i]!r} new={new[i]!r}"
    return None


# ---------- runners ----------
class ProcessRunner:
    def __init__(self, root, module):
        self.p = subprocess.Popen([sys.executable, "-c", WORKER, root, module],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def __call__(self, fname, args):
        data = pickle.dumps((fname, args))
        self.p.stdin.write(len(data).to_bytes(8, "big") + data)
        self.p.stdin.flush()
        return pickle.loads(self.p.stdout.read(int.from_bytes(self.p.stdout.read(8), "big")))


def load_as(path, alias):
    spec = importlib.util.spec_from_file_location(alias, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def in_process(mod):
    def run(fname, args):
        args = copy.deepcopy(args)
        try:
            return ("return", getattr(mod, fname)(*args), args, "")
        except Exception as e:
            return ("raise", type(e).__name__, args, "")
    return run


# ---------- the one property, two backends ----------
def check(fname, strategy, old_run, new_run, backend, n):
    @settings(backend=backend, max_examples=n, database=None, deadline=None,
              suppress_health_check=list(HealthCheck))
    @given(strategy)
    def same_behaviour(args):
        diff = explain(old_run(fname, copy.deepcopy(args)), new_run(fname, copy.deepcopy(args)))
        assert diff is None, diff

    try:
        same_behaviour()
        return "equivalent", None
    except AssertionError as e:
        example = next((note for note in getattr(e, "__notes__", []) if "args=" in note), "")
        return "DIFFERS", f"{example.strip()}  ->  {e}"


def main():
    repo, base, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    only = sys.argv[5] if len(sys.argv) > 5 else None
    base_root = snapshot(repo, base)
    for f, fname in changed_functions(repo, base):
        if only and fname != only:
            continue
        module = Path(f).with_suffix("").as_posix().replace("/", ".")
        new_mod = load_as(Path(repo, f), f"new_{module}")
        strategy = strategy_for(getattr(new_mod, fname))
        if mode == "symbolic":
            old_run = in_process(load_as(Path(base_root, f), f"old_{module}"))
            new_run = in_process(new_mod)
            backend = "crosshair"
        else:
            old_run, new_run = ProcessRunner(base_root, module), ProcessRunner(repo, module)
            backend = "hypothesis"
        t = time.perf_counter()
        verdict, detail = check(fname, strategy, old_run, new_run, backend, n)
        dt = time.perf_counter() - t
        print(f"{'✅' if verdict == 'equivalent' else '❌'} {fname:<14} {verdict:<10} {dt:6.2f}s")
        if detail:
            print(f"     {detail}")


if __name__ == "__main__":
    main()
