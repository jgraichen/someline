# pylint: disable=missing-docstring,invalid-name


from functools import partial

import build123d as b

from someline.someline import make_box, make_handle, make_wall_cutout
from someline.util import Project

WIDTH = 30.0
HEIGHT = 19.2

INNER_ROW_SIZE = 34.25
OUTER_ROW_SIZE = 33.25


def unit_to_length(u: int):
    if u < 3:
        return u * OUTER_ROW_SIZE
    else:
        return 2 * OUTER_ROW_SIZE + (u - 2) * INNER_ROW_SIZE


def make(units: int, width: float = WIDTH):
    length = unit_to_length(units)

    with b.BuildPart() as part:
        with make_box(length, width, HEIGHT) as box:
            with b.Locations((0.0, width, HEIGHT)):
                if units < 2:
                    handle = make_handle(length=length)
                else:
                    handle = make_handle(length=28)
                b.add(handle)

        b.add(box)

        if units > 1:
            pad, pocket = make_wall_cutout(
                outer_width=5.0,
                inner_width=4.0,
                depth=2.2,
                height=12.5,
            )

            sym_plane = b.Plane.XZ.offset(-width / 2)
            with b.BuildPart(mode=b.Mode.PRIVATE) as padM:
                b.add(pad)
                b.mirror(pad, about=sym_plane)
            with b.BuildPart(mode=b.Mode.PRIVATE) as pocketM:
                b.add(pocket)
                b.mirror(pocket, about=sym_plane)

            with b.Locations((OUTER_ROW_SIZE, 0.0, 0.0)):
                with b.GridLocations(
                    INNER_ROW_SIZE, 0, units - 1, 1, align=b.Align.MIN
                ):
                    b.add(padM)
                    b.add(pocketM, mode=b.Mode.SUBTRACT)

    return part.part


def make_cap():
    width = 18.5
    length = 21.6

    cr = 2.3 / 2
    cz = 2.5

    with b.BuildPart() as clip:
        with b.BuildSketch(b.Plane.XZ):
            with b.BuildLine():
                b.Polyline(
                    [
                        (0.0, 0.0),
                        (0.0, 0.48),
                        (0.8, 0.85),
                        (0.8, 1.85),
                        (0.0, 2.22),
                        (0.0, 2.9),
                        (3.0, 2.9),
                        (5.0, 0),
                    ],
                    close=True,
                )
            b.make_face()
        b.extrude(amount=4, both=True)

        top = clip.edges().filter_by(b.Axis.Y).group_by(b.Axis.Z)[-1].group_by(b.Axis.X)
        b.chamfer(top[0], length=0.2)

    with b.BuildPart() as cutout:
        with b.BuildSketch(b.Plane.XZ):
            with b.BuildLine():
                b.Polyline(
                    [
                        (0.0, 0.0),
                        (0.4, 0.6),
                        (1.4, 0.6),
                        (1.8, 0),
                    ],
                    close=True,
                )
            b.make_face()
        b.extrude(amount=10, both=True)

    with b.BuildPart() as part:
        b.Box(length, width, 5.2, align=(b.Align.MIN, b.Align.CENTER, b.Align.MIN))
        b.fillet(part.edges().filter_by(b.Axis.Z).group_by(b.Axis.X)[-1], radius=1.5)

        with b.BuildSketch(b.Plane.XZ) as sk:
            with b.Locations((1, 4.2)):
                b.Rectangle(length, 3, align=b.Align.MIN)
                b.chamfer(sk.vertices(), length=0.5)
            with b.Locations((2.2, cz)):
                b.Circle(radius=cr)
                b.Rectangle(1.7, 3, align=(b.Align.CENTER, b.Align.MIN))

        b.extrude(amount=-100, both=True, mode=b.Mode.SUBTRACT)

        yzx = part.edges().filter_by(b.Axis.Y).group_by(b.Axis.Z)[0].group_by(b.Axis.X)
        b.chamfer(yzx[0], length=1)
        b.chamfer(yzx[-1], length=0.6)

        with b.BuildSketch(b.Plane.XY.offset(cz - cr)) as skb:
            with b.Locations((2.2, 0)):
                b.Rectangle(
                    length - 2.2 - 1.2,
                    width - (1.2 * 2),
                    align=(b.Align.MIN, b.Align.CENTER),
                )
                b.fillet(skb.vertices().group_by(b.Axis.X)[-1], radius=0.2)

        b.extrude(amount=10, mode=b.Mode.SUBTRACT)

        with b.Locations((12.0, 0, 0)):
            with b.GridLocations(3.0, 0, 3, 1):
                b.add(cutout.part, mode=b.Mode.SUBTRACT)

        with b.Locations((12.2, 0, cz - cr)):
            b.add(clip.part)

    return part.part


project = Project("someline-15", default_color=b.Color(0xFF6A13))
project.add("U0", partial(make, units=1, width=25.0))

for i in range(1, 6):
    project.add(f"U{i}", partial(make, units=i))

project.add("cap", make_cap)


if __name__ == "__main__":
    project.main()
