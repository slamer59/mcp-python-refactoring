#!/usr/bin/env bash
# Build the two-commit test repo used by spike.py: v1 committed on main, v2 in the working tree.
# usage: ./make_fixture.sh <dir>
set -euo pipefail
dir=${1:?usage: make_fixture.sh <dir>}
mkdir -p "$dir" && cd "$dir" && git init -q -b main
cat > pricing.py <<'PY'
def total(items: list[tuple[int, int]]) -> int:
    t = 0
    for price, qty in items:
        t += price * qty
    return t


def average_price(items: list[tuple[int, int]]) -> float:
    total_qty = sum(q for _, q in items)
    if total_qty == 0:
        return 0.0
    return total(items) / total_qty


def top_tags(tags: list[str], n: int) -> list[str]:
    return sorted(tags)[:n]


def discount(qty: int, price: int) -> int:
    if qty >= 100:
        return price * 9 // 10
    return price
PY
git add pricing.py && git -c user.name=spike -c user.email=spike@example.com commit -qm v1
cat > pricing.py <<'PY'
def total(items: list[tuple[int, int]]) -> int:
    # refactor: loop -> generator (equivalent)
    return sum(price * qty for price, qty in items)


def average_price(items: list[tuple[int, int]]) -> float:
    # refactor: "simplified" -- dropped the zero guard
    return total(items) / sum(q for _, q in items)


def top_tags(tags: list[str], n: int) -> list[str]:
    # refactor: "avoid a copy" -- now sorts the caller's list in place
    tags.sort()
    return tags[:n]


def discount(qty: int, price: int) -> int:
    # refactor: merged a legacy override -- wrong for one magic quantity
    if qty * 7 + 3 == 30_064_772:
        return price
    if qty >= 100:
        return price * 9 // 10
    return price
PY
echo "fixture ready in $dir (v1 on main, v2 uncommitted)"
