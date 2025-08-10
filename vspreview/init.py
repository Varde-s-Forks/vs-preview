from __future__ import annotations

from . import qt_patch  # noqa: F401

import logging
import os
import signal
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence

from PyQt6.QtWidgets import QApplication

from .core.logger import set_log_level, setup_logger
from ._metadata import __version__

# import vsenv as early as possible:
# This is so other modules cannot accidentally use and lock us into a different policy.
from .core.vsenv import set_vsengine_loop
from .main import MainWindow
from .plugins import get_installed_plugins
from .plugins.abstract import FileResolverPlugin, ResolvedScript
from .plugins.install import (
    install_plugins,
    plugins_commands,
    print_available_plugins,
    uninstall_plugins,
)

__all__ = ["main"]


def get_resolved_script(filepath: Path,  no_exit: bool) -> tuple[ResolvedScript, FileResolverPlugin | None]:
    for plugin in get_installed_plugins(FileResolverPlugin, False).values():
        if plugin.can_run_file(filepath):
            return plugin.resolve_path(filepath), plugin

    if not filepath.exists():
        from .utils import exit_func

        logging.error("Script or file path is invalid.")
        exit_func(1, no_exit)

    return ResolvedScript(filepath, str(filepath)), None


def main(_args: Sequence[str] | None = None, no_exit: bool = False) -> int:
    from .utils import exit_func

    if _args is None:
        _args = sys.argv[1:]

    parser = ArgumentParser(prog="VSPreview")

    # If the first arg is NOT a command, then script_path is expected
    if _args and _args[0] not in plugins_commands:
        parser.add_argument(
            "script_path",
            type=str,
            help="Path to Vapoursynth script or video file(s)",
        )

    # Global options
    parser.add_argument("--version", "-v", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--preserve-cwd", "-c", action="store_true", help="Do not chdir to script parent directory")
    parser.add_argument("-f", "--frame", type=int, help="Frame to load initially (defaults to 0)")
    parser.add_argument("--vscode-setup", type=str, choices=["override", "append", "ignore"], nargs="?", const="append",
                        help="Installs launch settings in cwd's .vscode")
    parser.add_argument("--verbose", action="store_true", help="Set the logging to verbose.")
    parser.add_argument("--force", action="store_true", help="Force the install of a plugin even if it exists already.")
    parser.add_argument("--no-deps", action="store_true", help="Ignore downloading dependencies.")
    parser.add_argument("--force-storage", action="store_true", default=False, help="Force override or local/global storage.")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser_add = subparsers.add_parser("install", help="Install new plugin(s).")
    parser_add.add_argument("plugins", nargs="*", help="List of the plugins to add.")

    parser_remove = subparsers.add_parser("uninstall", help="Uninstall existing plugin(s).")
    parser_remove.add_argument("plugins", nargs="*", help="List of the plugins to remove.")

    parser_update = subparsers.add_parser("update", help="Update existing plugin(s).")
    parser_update.add_argument("plugins", nargs="*", help="List of the plugins to update.")

    parser_available = subparsers.add_parser("available", help="Show available plugins.")
    parser_available.add_argument("plugins", nargs="*", help="List of the plugins available.")

    args = parser.parse_args(_args)

    setup_logger()

    if args.verbose:
        from vstools import VSDebug

        set_log_level(logging.DEBUG, logging.DEBUG)
        VSDebug(use_logging=True)
    else:
        set_log_level(logging.WARNING)

    if args.vscode_setup is not None:
        from .api.other import install_vscode_launch

        install_vscode_launch(args.vscode_setup)

        return exit_func(0, no_exit)

    if args.command in plugins_commands:
        if args.command == "available":
            print_available_plugins()
        elif args.command == "install":
            install_plugins(args.plugins, args.force, args.no_deps)
        elif args.command == "uninstall":
            uninstall_plugins(args.plugins)
        elif args.command == "update":
            uninstall_plugins(args.plugins, True)
            install_plugins(args.plugins, True, args.no_deps)
        return exit_func(0, no_exit)

    if not getattr(args, "script_path", None):
        logging.error("Script/Video path required.")
        parser.print_help()
        return exit_func(1, no_exit)

    script, file_resolve_plugin = get_resolved_script(Path(args.script_path).resolve(), no_exit)

    if (
        file_resolve_plugin
        and hasattr(file_resolve_plugin, "_config")
        and file_resolve_plugin._config.namespace == "dev.setsugen.vssource_load"
    ):
        args.preserve_cwd = True

    if not args.preserve_cwd:
        os.chdir(script.path.parent)

    first_run = not hasattr(main, "app")

    if first_run:
        main.app = QApplication(sys.argv)
        set_vsengine_loop()
    else:
        from .core.vsenv import get_current_environment, make_environment

        make_environment()
        get_current_environment().use()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    arguments = script.arguments.copy()

    def _parse_arg(kv: str) -> tuple[str, str | int | float]:
        v: str | int | float
        k, v = kv.split("=", maxsplit=1)

        try:
            v = int(v)
        except ValueError:
            try:
                v = float(v)
            except ValueError:
                ...

        return k.strip("--"), v

    # if args.plugins:
    #     if file_resolve_plugin._config.namespace == "dev.setsugen.vssource_load":
    #         additional_files = list[Path](
    #             Path(filepath).resolve() for filepath in args.plugins
    #         )
    #         arguments.update(additional_files=additional_files)
    #     else:
    #         arguments |= {k: v for k, v in map(_parse_arg, args.plugins)}

    main.main_window = MainWindow(
        Path(os.getcwd()) if args.preserve_cwd else script.path.parent,
        no_exit,
        script.reload_enabled,
        args.force_storage,
    )
    main.main_window.load_script(
        script.path,
        list(arguments.items()),
        False,
        args.frame or None,
        script.display_name,
        file_resolve_plugin,
    )

    ret_code = main.app.exec()

    if no_exit:
        from .core.vsenv import _dispose

        main.main_window.hide()

        _dispose()

    return exit_func(ret_code, no_exit)


if __name__ == "__main__":
    main()
