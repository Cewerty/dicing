#!/usr/bin/env bash
# Smoke test of the *built* package: install it into a clean virtualenv and run the CLI the way
# a user would. Catches packaging problems that unit tests can't see: a missing console-script
# entry point, or dice_grammar.lark not shipped inside the wheel.
#
# Usage:
#   uv build && bash scripts/cli_smoke_test.sh     # newest wheel from dist/
#   bash scripts/cli_smoke_test.sh --testpypi 0.4.0  # the release published on TestPyPI
set -euo pipefail

mode=wheel
if [[ "${1:-}" == "--testpypi" ]]; then
    mode=testpypi
    version=${2:?"usage: $0 --testpypi VERSION"}
elif [[ $# -gt 0 ]]; then
    echo "usage: $0 [--testpypi VERSION]" >&2
    exit 2
fi

if [[ "$mode" == wheel ]]; then
    wheel=$(ls -t dist/dicing-*.whl 2>/dev/null | head -n 1 || true)
    if [[ -z "$wheel" ]]; then
        echo "smoke: no wheel in dist/ — run 'uv build' first" >&2
        exit 1
    fi
    wheel=$(cd "$(dirname "$wheel")" && pwd)/$(basename "$wheel")
fi

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT
uv venv --quiet "$workdir/venv"
if [[ -d "$workdir/venv/bin" ]]; then bin="$workdir/venv/bin"; else bin="$workdir/venv/Scripts"; fi

if [[ "$mode" == wheel ]]; then
    uv pip install --quiet --python "$workdir/venv" "$wheel"
    package=$(basename "$wheel")
else
    # Only dicing itself comes from TestPyPI (--no-deps): anyone can upload there, so its
    # dependencies are installed from the real PyPI to avoid dependency confusion.
    # The TestPyPI index is updated with a delay after upload, hence the retries.
    for attempt in $(seq 1 10); do
        if uv pip install --quiet --refresh --no-deps --python "$workdir/venv" \
            --index-url https://test.pypi.org/simple/ "dicing==$version"; then
            break
        fi
        if [[ "$attempt" == 10 ]]; then
            echo "smoke: dicing==$version is not available on TestPyPI" >&2
            exit 1
        fi
        echo "smoke: dicing==$version not on TestPyPI yet, retry $attempt/10 in 30s..."
        sleep 30
    done
    "$bin/python" -c "
import importlib.metadata as metadata
print('\n'.join(r for r in metadata.requires('dicing') or [] if 'extra ==' not in r))
" > "$workdir/requirements.txt"
    uv pip install --quiet --python "$workdir/venv" --index-url https://pypi.org/simple/ -r "$workdir/requirements.txt"
    package="dicing==$version from TestPyPI"
fi

# Run outside the source tree, so only the installed package can be imported.
cd "$workdir"

check() {
    local name=$1 expected=$2 actual=$3
    if [[ "$actual" != "$expected" ]]; then
        echo "smoke: FAIL $name: expected '$expected', got '$actual'" >&2
        exit 1
    fi
    echo "smoke: ok   $name"
}

echo "smoke: testing $package"
"$bin/dicing" --version >/dev/null && echo "smoke: ok   --version"

# Seeded rolls are reproducible across Python versions: 4d6kh3+2 with seed 42 is always 15.
check "seeded total" "15" "$("$bin/dicing" "4d6kh3+2" --seed 42 --total | tr -d '\r')"

json_total=$("$bin/dicing" "4d6kh3+2" --seed 42 --json | "$bin/python" -c "import json, sys; print(json.load(sys.stdin)['total'])" | tr -d '\r')
check "json total" "15" "$json_total"

"$bin/dicing" "4d6kh3+2" --seed 42 | grep -q "dropped" && echo "smoke: ok   breakdown shows dropped dice"

"$bin/python" -m dicing "1d20+5" --total >/dev/null && echo "smoke: ok   python -m dicing"

set +e
"$bin/dicing" "abc" 2>/dev/null
code=$?
set -e
check "invalid notation exit code" "2" "$code"

echo "smoke: all checks passed"
