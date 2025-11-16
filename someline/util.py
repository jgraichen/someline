# pylint: disable=missing-docstring


import os
import re
from fnmatch import fnmatch
from functools import cached_property
from typing import Callable, Generator, Iterable

import click
from build123d import (
    Color,
    Compound,
    Location,
    Part,
    Shape,
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
        filename: str | None = None,
    ):
        self.name = name
        self.color = color
        self.grid = grid
        self.export = export
        self._fn = fn
        self.filename = filename

        if not self.filename:
            self.filename = name

    @cached_property
    def part(self):
        part = self._fn()
        part.label = self.name
        if self.color:
            part.color = self.color
        return part


PlateFunc = Callable[..., Iterable[Iterable[Model]]]


class Plate:
    ALIGN_Y = True

    def __init__(
        self,
        name: str,
        fn: PlateFunc,
        padding: int = 1,
        filename: str | None = None,
    ):
        self.fn = fn
        self.name = name
        self.padding = padding
        self.filename = filename

        if not self.filename:
            self.filename = os.path.join("plate", name)

    @cached_property
    def rows(self):
        return self.fn()

    @cached_property
    def compound(self):
        parts = []

        rbb = [[m.part.bounding_box(tolerance=0.1) for m in r] for r in self.rows]
        rsx = [sum(bb.size.X for bb in r) + (len(r) - 1) * self.padding for r in rbb]
        mrx = max(rsx)

        y = 0
        for row, bbs, sx in zip(self.rows, rbb, rsx):
            y = y - max(bb.size.Y for bb in bbs) - self.padding

            if Plate.ALIGN_Y:
                x = (mrx - sx) / 2
                x_pad = self.padding
            else:
                x = 0
                x_pad = (mrx - sum(bb.size.X for bb in bbs)) / (len(row) - 1)

            for model, bb in zip(row, bbs):
                part = model.part

                if abs(bb.min) > 0.1:
                    min = bb.min.reverse()
                    loc = Location(
                        (
                            x + round(min.X, 2),
                            y + round(min.Y, 2),
                            round(min.Z, 2),
                        )
                    )
                else:
                    loc = Location((x, y))

                parts.append(loc * part)
                x = x + bb.size.X + x_pad

        return Compound(label=self.name, children=parts)


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
        self._plates: dict[str, Plate] = {}

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
        filename: str | None = None,
    ):
        if name in self._models:
            raise KeyError(f"Name {name} already taken")

        self._models[name] = Model(
            name,
            fn,
            color=(color or self.default_color),
            grid=grid,
            export=export,
            filename=filename,
        )

    def plate(self, name: str, **kwargs):
        def decorator(fn):
            if name in self._plates:
                raise KeyError(f"Name {name} already taken")

            self._plates[name] = Plate(name, fn, **kwargs)

        return decorator

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


@_main.command(name="plate")
@click.argument("name")
@_pass_project
def _plate(project: Project, name: str):
    import ocp_vscode  # pylint: disable=C0415

    ocp_vscode.show(project._plates[name].compound)


@_main.command(name="export")
@click.option("--list", "_list", is_flag=True, default=False)
@click.argument("directory", default="")
@_pass_project
def _export(project: Project, _list: bool, directory: str):
    if not directory:
        directory = os.path.join("export", project.name)

    models = [model for model in project if model.export]
    plates = [plate for plate in project._plates.values()]

    if _list:
        for model in models:
            print(os.path.join(directory, f"{model.filename}.step"))
            print(os.path.join(directory, f"{model.filename}.stl"))
        for plate in plates:
            print(os.path.join(directory, f"{plate.filename}.step"))

        return

    for model in models:
        _export_step(model.part, os.path.join(directory, f"{model.filename}.step"))
        _export_stl(model.part, os.path.join(directory, f"{model.filename}.stl"))

    for plate in plates:
        _export_step(plate.compound, os.path.join(directory, f"{plate.filename}.step"))


def _export_stl(shape: Shape, file: str):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    export_stl(shape, file)


def _export_step(shape: Shape, file: str):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    export_step(shape, file, timestamp="0000-00-00T00:00:00")
