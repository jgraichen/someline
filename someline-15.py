# pylint: disable=missing-docstring,invalid-name


import build123d as b

from someline.someline import make_box, make_cutout, make_handle
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


def make(units: int, width: int = WIDTH):
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
            pad, pocket = make_cutout(
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


project = Project("someline-15")


@project.model("Someline-15-U0", color=b.Color(0xFF6A13))
def u0():
    return make(units=1, width=25.0)


@project.model("Someline-15-U1", color=b.Color(0xFF6A13))
def u1():
    return make(units=1)


@project.model("Someline-15-U2", color=b.Color(0xFF6A13))
def u2():
    return make(units=2)


@project.model("Someline-15-U3", color=b.Color(0xFF6A13))
def u3():
    return make(units=3)


@project.model("Someline-15-U4", color=b.Color(0xFF6A13))
def u4():
    return make(units=4)


@project.model("Someline-15-U5", color=b.Color(0xFF6A13))
def u5():
    return make(units=5)


if __name__ == "__main__":
    project.main()
