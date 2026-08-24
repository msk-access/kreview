#!/usr/bin/env bash
# Create an isolated environment for local research work.
#
# Never install into the base interpreter — a base-env install of torch pulled
# setuptools past 81 and removed pkg_resources, which is exactly what this project's
# `setuptools<81` pin exists to prevent (.agents/memory/feedback-isolated-envs-only.md).
#
#   bash scripts/make_research_env.sh                  # analysis stack only
#   bash scripts/make_research_env.sh --with-ml        # + torch/tabicl (large; GPU work
#                                                      #   belongs on the cluster)
#   bash scripts/make_research_env.sh --path ~/envs/kr # somewhere other than .venv-research
#
# uv is preferred and used when present; otherwise python -m venv. Either way the script
# refuses to proceed unless the interpreter it is about to install into really is isolated.
set -euo pipefail

ENV_PATH=".venv-research"
WITH_ML=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-ml) WITH_ML=1; shift ;;
        --path)    ENV_PATH="${2:?--path needs a directory}"; shift 2 ;;
        -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

if command -v uv >/dev/null 2>&1; then
    echo "creating $ENV_PATH with uv"
    uv venv "$ENV_PATH"
    PIP=(uv pip install --python "$ENV_PATH/bin/python")
else
    echo "creating $ENV_PATH with python -m venv (uv not found)"
    python3 -m venv "$ENV_PATH"
    PIP=("$ENV_PATH/bin/python" -m pip install)
fi

# The check that would have caught today's mistake in one second: a directory that looks
# like a venv is not one, and its `python` may be a symlink to the base interpreter.
PREFIX="$("$ENV_PATH/bin/python" -c 'import sys; print(sys.prefix)')"
BASE="$("$ENV_PATH/bin/python" -c 'import sys; print(sys.base_prefix)')"
if [[ ! -f "$ENV_PATH/pyvenv.cfg" || "$PREFIX" == "$BASE" ]]; then
    echo "FATAL: $ENV_PATH is not an isolated environment (prefix=$PREFIX base=$BASE)." >&2
    echo "Refusing to install — this is how packages end up in the base interpreter." >&2
    exit 1
fi
echo "isolation confirmed: prefix=$PREFIX"

"${PIP[@]}" -q --upgrade pip
"${PIP[@]}" -q -e ".[test]"

if [[ "$WITH_ML" == "1" ]]; then
    echo "installing the ML stack (torch, tabicl) — several hundred MB"
    "${PIP[@]}" -q "torch>=2.0" "tabicl>=2.1" transformers
fi

cat <<MSG

Ready. Activate with:
    source $ENV_PATH/bin/activate
or call it directly without activating:
    $ENV_PATH/bin/python scripts/research_analyses/<script>.py
MSG
