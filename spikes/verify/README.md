# Spike: `verify` — behaviour-equivalence check for refactors

**Question:** can we check that a refactor didn't change behaviour by running the old and new
version of each changed function on the same inputs — and would that cover enough real code
to be worth building?

**Answer:** the technique works (both engines catch real bugs, on Python 3.13 and 3.14), but
plain functions alone cover only ~12–32% of changed code. It is worth building only if v1 also
handles **methods** and **compatible signature changes** (see [Proposed v1 scope](#proposed-v1-scope)).

## How it works

1. `git diff <base>` → functions whose source changed (parsed with `ast`).
2. The base commit is extracted with `git archive` (no git state touched); "new" is the working tree.
3. One Hypothesis property compares old vs new on the same inputs: return value, exception type,
   mutation of the arguments, and stdout. Two backends:
   - **random** — Hypothesis's default backend; old and new each run in their own worker process.
   - **symbolic** — the same property with `@settings(backend="crosshair")` (`hypothesis[crosshair]`);
     both versions load into one process, because symbolic values can't cross a process boundary.
4. On a difference, Hypothesis shrinks to a minimal failing input.

## Run it

```bash
./make_fixture.sh /tmp/verify-fixture
uv run --no-project --python 3.14 --with "hypothesis[crosshair]" \
    python spike.py /tmp/verify-fixture main random 500
uv run --no-project --python 3.14 --with "hypothesis[crosshair]" \
    python spike.py /tmp/verify-fixture main symbolic 100 top_tags

python measure.py /path/to/some/repo 300   # how much of a repo's history is checkable
```

Pass `--python` explicitly: with `--no-project`, `uv` otherwise picks its own default interpreter.

## Results: trial (identical on Python 3.13 and 3.14)

| Refactor in the fixture | Random | Symbolic (CrossHair) |
|---|---|---|
| Removed a zero guard | ❌ caught in 0.02s — `([],)` | ❌ caught in 0.3s |
| Sorts the caller's list in place | ❌ caught in 0.2s — `(['0', ''], 0)` | **missed** at 20 examples; caught at 100 (3s) |
| Wrong result for one magic quantity | **missed** | ❌ caught in 0.2s — `(4294967, 1)` |
| Loop → `sum()` (genuinely equivalent) | ✅ in 0.3s | ✅ in 1.7s at 20 examples; **>180s at 300** |

Lessons:
- **Each engine caught a bug the other missed**, so run both: random first (fast), then symbolic.
- **Symbolic is slowest when nothing is wrong** (it keeps searching), so budget it by
  **wall-clock time per function** (e.g. 10s), not by example count.
- Hypothesis already harvests literals from the code under test (`.hypothesis/constants`); the
  fixture's magic value is computed (`qty * 7 + 3 == …`) so that this doesn't find it trivially.

## Results: how much real code is checkable

`measure.py` walks a repo's history and classifies every *modified* function (added/removed
functions excluded). It is a **static heuristic**: I/O is detected from call names, one level deep
within the module, so it misses some I/O and flags some false positives.

| Repo | Modified functions | **Checkable** | Method | Signature changed | Does I/O | Async |
|---|---|---|---|---|---|---|
| gemseo (scientific library, 300 commits) | 5,895 | **31.5%** | 25.7% | 22.6% | 20.1% | — |
| a private web service (300 commits) | 2,014 | **22.0%** | 23.5% | 15.0% | 17.3% | 18.0% |
| a code-exploration MCP tool (127 commits) | 452 | **12.4%** | 18.4% | 20.4% | 47.3% | 0.4% |
| this repo (17 commits) | 35 | **28.6%** | 20.0% | 20.0% | 22.9% | 2.9% |

I/O is **not** the main blocker (except in the I/O-heavy tool). Methods and signature changes
together account for ~35–48% of modified functions.

## Proposed v1 scope

- **Methods:** build the instance from `self` recorded during the test run, or generate it from
  `__init__`'s type hints.
- **Compatible signature changes:** when the old call still binds to the new signature (e.g. an
  added parameter with a default), call both versions with the old arguments.
- **Symbolic mode** with a per-function time budget, run after random mode.
- Still skipped and reported: I/O, nondeterminism, incompatible signature changes.

Rough estimate if v1 recovers about half of the methods and signature changes: ~55% checkable for
a gemseo-like codebase, ~40% for the web service, ~30% for the I/O-heavy tool. Not worth it for
I/O-heavy code in any version.

## Known spike shortcuts

Not production code: no per-call process isolation (one long-lived worker per version), no I/O
audit hook, no recorded inputs, no time/memory limits, worker pipes aren't closed (harmless
`ResourceWarning`s), and only module-level functions are compared.
