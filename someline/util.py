# pylint: disable=missing-docstring


import os
import re
from functools import wraps
from typing import Callable, Optional

import click
from build123d import Color, Part, export_step, export_stl

STEP_TIMESTAMP_PATTERN = re.compile("FILE_NAME.*'(\\d+-\\d+-\\d+T\\d+:\\d+:\\d+)'")

ModelFunc = Callable[..., Part]


class Project:
    def __init__(self, name: str, default_color: Optional[Color] = None) -> None:
        self.name = name
        self.default_color = default_color
        self._models = {}
        self._results = {}

    def names(self):
        return list(self._models)

    def __getitem__(self, name):
        if name not in self._results:
            self._results[name] = self._models[name]()
        return self._results[name]

    def __iter__(self):
        for name in self._models:
            yield self[name], name

    def define(
        self,
        name: str,
        fn: ModelFunc,
        color: Optional[Color] = None,
        args: ... = {},
    ):
        @wraps(fn)
        def wrapper():
            part = fn(**args)
            part.label = name
            if color:
                part.color = color
            elif self.default_color:
                part.color = self.default_color
            return part

        if name in self._models:
            raise KeyError(f"Name {name} already taken")

        self._models[name] = wrapper
        return wrapper

    def model(
        self, name: str, color: Optional[Color] = None
    ) -> Callable[[ModelFunc], ModelFunc]:
        def decorator(fn: ModelFunc) -> ModelFunc:
            return self.define(name, fn, color)

        return decorator

    def main(self):
        _main(obj=self)  # pylint: disable=E1120


_pass_project = click.make_pass_decorator(Project)


@click.group(invoke_without_command=True)
@click.pass_context
def _main(ctx: click.Context):
    if not ctx.invoked_subcommand:
        ctx.invoke(_run)


@_main.command(name="run")
@click.argument("text", default="")
@_pass_project
def _run(project: Project, text: str):
    import ocp_vscode  # pylint: disable=C0415

    if text:
        for name in project.names():
            if text in name:
                ocp_vscode.show(project[name])
                break
        else:
            click.echo("No match found for: {text}")
            raise click.Abort()
    else:
        ocp_vscode.show(*project, names=project.names())


@_main.command(name="export")
@click.option("--list", "_list", is_flag=True, default=False)
@click.argument("directory", default="")
@_pass_project
def _export(project: Project, _list: bool, directory: str):
    if not directory:
        directory = os.path.join("export", project.name)

    if _list:
        for name in project.names():
            print(os.path.join(directory, f"{name}.step"))
            print(os.path.join(directory, f"{name}.stl"))
        return

    for model, name in project:
        os.makedirs(directory, exist_ok=True)

        file = os.path.join(directory, f"{name}.step")
        export_step(model, file)

        # Remove timestamp from STEP exports because otherwise git
        # would always have changes.
        with open(file, "rb+") as fd:
            for line in fd:
                if not line.startswith(b"FILE_NAME"):
                    continue

                text = line.decode("utf-8")
                match = STEP_TIMESTAMP_PATTERN.match(text)
                if match:
                    ts = match.group(1).encode("utf-8")
                    fd.seek(-len(line) + line.index(ts), 1)
                    fd.write(b"0000-00-00T00:00:00")
                    break

        export_stl(model, os.path.join(directory, f"{name}.stl"))
