#!/usr/bin/env bash

# Find and change to project root directory
find_project_root() {
  local dir="$PWD"

  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/flake.nix" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done

  echo "Error: Could not find project root (flake.nix)" >&2
  return 1
}

# Change to project root or exit
if ! cd "$(find_project_root)"; then
  exit 1
fi

export PYTHONPATH=".:$PYTHONPATH"

# Run command and collect output
run_quiet() {
  tool_name="$1"
  shift

  echo -ne "\033[90m::\033[0m Running \033[34m$tool_name\033[0m "

  if ! output=$("$@" 2>&1); then
    echo -e "\033[31mERROR\033[0m\n\033[90m===\033[0m \033[34m$tool_name\033[0m \033[90mfailed\033[0m \033[90m===\033[0m\n$output\n\n"

    return 1
  fi

  echo -e "\033[32mOK\033[0m"
  return 0
}

# shellcheck disable=SC2068
run_quiet "ruff format" ruff format $@

run_quiet "autoflake" autoflake \
  --recursive \
  --in-place \
  --expand-star-imports \
  --remove-all-unused-imports \
  --ignore-init-module-imports \
  --remove-duplicate-keys \
  --remove-unused-variables \
  mubot/ollama

run_quiet "vulture" python -m vulture --min-confidence 100 mubot/ollama
run_quiet "pylint" python -m pylint mubot.ollama
run_quiet "mypy" python -m mypy --pretty -m mubot.ollama

# Run all commands, collecting exit status
run_quiet "ruff check" ruff check --line-length 102 --fix

# shellcheck disable=SC2068
run_quiet "ruff format" ruff format $@
