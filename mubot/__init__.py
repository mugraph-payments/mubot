#!/usr/bin/env python3

import os
import pkgutil
import sys
import asyncio
from importlib import import_module
from pathlib import Path


def find_executables() -> list[str]:
    commands = []
    for path in os.environ["PATH"].split(os.pathsep):
        if Path(path).exists():
            for cmd in os.listdir(path):
                if cmd.startswith("mubot-"):
                    commands.append(cmd[6:])  # Remove 'mubot-' prefix
    return sorted(set(commands))


def find_modules() -> list[tuple[str, str]]:
    modules = []
    mubot_package = import_module("mubot")

    for module_info in pkgutil.iter_modules(mubot_package.__path__, "mubot."):
        try:
            module = import_module(module_info.name)
            if hasattr(module, "main"):
                name = module_info.name.split(".")[-1]  # Get part after last dot
                doc = module.main.__doc__ or "No description available"
                modules.append((name, doc.split("\n")[0].strip()))
        except ImportError:
            continue

    return sorted(modules)


def main() -> None:
    if len(sys.argv) < 2:
        # List available commands and modules
        print("Available commands:")
        for cmd in find_executables():
            print(f"  {cmd}")
        print("\nAvailable modules:")
        for name, desc in find_modules():
            print(f"  {name:<20} {desc}")
        sys.exit(0)

    subcommand = sys.argv[1]

    # Try loading as a module first
    try:
        module_name = f"mubot.{subcommand}"
        if module_name != "mubot.__main__":  # Ignore __main__
            module = import_module(module_name)
            if hasattr(module, "main"):
                # Check if main is a coroutine function
                if asyncio.iscoroutinefunction(module.main):
                    asyncio.run(module.main())
                else:
                    module.main()
                sys.exit(0)
    except ImportError:
        pass

    # Fall back to executable if no module is found
    executable = f"mubot-{subcommand}"
    for path in os.environ["PATH"].split(os.pathsep):
        exe_path = Path(path) / executable
        if exe_path.exists() and os.access(exe_path, os.X_OK):
            os.execvp(executable, [executable] + sys.argv[2:])  # noqa: S606

    print(f"Error: No command or module found for '{subcommand}'", file=sys.stderr)
    sys.exit(1)
