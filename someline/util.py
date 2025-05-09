# pylint: disable=missing-docstring


import os
import re
from fnmatch import fnmatch
from functools import cached_property
from typing import Callable, Generator

import click
from build123d import (
    Color,
    Compound,
    Location,
    Part,
    export_step,
    export_stl,
    pack,
)

STEP_TIMESTAMP_PATTERN = re.compile("FILE_NAME.*'(\\d+-\\d+-\\d+T\\d+:\\d+:\\d+)'")

ModelFunc = Callable[..., Part]


class Model:
    def __init__(
        self,
        name: str,
        fn: ModelFunc,
        *,  # required customizations as keyword arguments:
        color: Color | None = None,
        export: bool = True,
        grid: tuple[float, float] | None = None,
    ):
        self.name = name
        self.color = color
        self.grid = grid
        self.export = export
        self._fn = fn

    @cached_property
    def part(self):
        part = self._fn()
        part.label = self.name
        if self.color:
            part.color = self.color
        return part


class Project:
    def __init__(
        self,
        name: str,
        *,  # require customizations as keyword arguments:
        default_color: Color | None = None,
        grid: tuple[float, float] | None = None,
        padding: int = 4,
    ) -> None:
        self.name = name
        self.grid = grid
        self.padding = padding
        self.default_color = default_color
        self._models = {}

    def names(self):
        return list(self._models)

    def __getitem__(self, name: str):
        return self._models[name]

    def __iter__(self) -> Generator[Model, None, None]:
        for name in self._models:
            yield self[name]

    def add(
        self,
        name: str,
        fn: ModelFunc,
        *,  # require customizations as keyword arguments:
        color: Color | None = None,
        grid: tuple[int, int] | None = None,
        export: bool = True,
    ):
        if name in self._models:
            raise KeyError(f"Name {name} already taken")

        self._models[name] = Model(
            name,
            fn,
            color=(color or self.default_color),
            grid=grid,
            export=export,
        )

    def assembly(self, pattern: str | None = None, force_pack: bool = False):
        if pattern:
            models = [m for m in self if fnmatch(m.name, pattern)]
        else:
            models = [m for m in self]

        if not models:
            return None

        if len(models) < 2:
            return Compound(
                label=self.name,
                children=[m.part for m in models],
            )

        if not force_pack and self.grid:
            parts = [
                Location((m.grid[0] * self.grid[0], m.grid[1] * -self.grid[1])) * m.part
                for m in models
            ]
        else:
            parts = pack([m.part for m in models], padding=self.padding, align_z=True)

        return Compound(
            label=self.name,
            children=parts,
        )

    def main(self):
        _main(obj=self)  # pylint: disable=E1120


_pass_project = click.make_pass_decorator(Project)


@click.group(invoke_without_command=True)
@click.pass_context
def _main(ctx: click.Context):
    if not ctx.invoked_subcommand:
        ctx.invoke(_run)


@_main.command(name="run")
@click.argument("pattern", default="")
@click.option("--pack", is_flag=True)
@_pass_project
def _run(project: Project, pattern: str, pack: bool):
    import ocp_vscode  # pylint: disable=C0415

    if pattern:
        if "*" not in pattern and "?" not in pattern and "[" not in pattern:
            pattern = f"*{pattern}*"

    assembly = project.assembly(pattern, force_pack=pack)
    if not assembly:
        click.echo(f"No match found for: {pattern}")
        raise click.Abort()

    ocp_vscode.show(assembly)


@_main.command(name="export")
@click.option("--list", "_list", is_flag=True, default=False)
@click.argument("directory", default="")
@_pass_project
def _export(project: Project, _list: bool, directory: str):
    if not directory:
        directory = os.path.join("export", project.name)

    models = [model for model in project if model.export]

    if _list:
        for model in models:
            print(os.path.join(directory, f"{model.name}.step"))
            print(os.path.join(directory, f"{model.name}.stl"))
        return

    for model in models:
        os.makedirs(directory, exist_ok=True)

        file = os.path.join(directory, f"{model.name}.step")
        export_step(model.part, file)

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

        export_stl(model.part, os.path.join(directory, f"{model.name}.stl"))
