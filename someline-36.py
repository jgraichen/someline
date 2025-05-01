# pylint: disable=missing-docstring,invalid-name


import build123d as b

from someline.someline import make_box, make_cutout, make_handle
from someline.util import Project

WIDTH = 41.2
HEIGHT = 33.7

INNER_ROW_SIZE = 24.5
OUTER_ROW_SIZE = 24.0

WALL_DEPTH = 1.6

LIT_PIN_DY = 3.8
LIT_PIN_LENGTH = 4.5
LIT_PIN_TOPW = 3.0
LIT_PIN_BOTW = 2.0
LIT_PIN_DEPTH = 5.0


def unit_to_length(u: int):
    if u < 3:
        return u * OUTER_ROW_SIZE
    else:
        return 2 * OUTER_ROW_SIZE + (u - 2) * INNER_ROW_SIZE


def lit_cutouts(length):
    with b.BuildPart(mode=b.Mode.PRIVATE) as cutout:
        with b.BuildSketch(b.Plane.YZ):
            with b.BuildLine():
                b.Polyline(
                    [
                        (-(LIT_PIN_BOTW / 2), -LIT_PIN_DEPTH),
                        (-(LIT_PIN_TOPW / 2), 0.0),
                        (+(LIT_PIN_TOPW / 2), 0.0),
                        (+(LIT_PIN_BOTW / 2), -LIT_PIN_DEPTH),
                        (-(LIT_PIN_BOTW / 2), -LIT_PIN_DEPTH),
                    ]
                )
            b.make_face()
        b.extrude(amount=LIT_PIN_LENGTH)
        b.fillet(
            cutout.edges().group_by(b.Axis.Z)[0].filter_by(b.Axis.X),
            radius=(LIT_PIN_BOTW / 3),
        )

    with b.Locations((0.0, LIT_PIN_DY, HEIGHT)):
        b.add(cutout, mode=b.Mode.SUBTRACT)
    with b.Locations((0.0, WIDTH - LIT_PIN_DY, HEIGHT)):
        b.add(cutout, mode=b.Mode.SUBTRACT)
    with b.Locations((length - LIT_PIN_LENGTH, LIT_PIN_DY, HEIGHT)):
        b.add(cutout, mode=b.Mode.SUBTRACT)
    with b.Locations((length - LIT_PIN_LENGTH, WIDTH - LIT_PIN_DY, HEIGHT)):
        b.add(cutout, mode=b.Mode.SUBTRACT)


def make(units: int):
    length = unit_to_length(units)

    with b.BuildPart() as part:
        with make_box(length, WIDTH, HEIGHT, wall_depth=WALL_DEPTH) as box:
            with b.Locations((0.0, WIDTH, HEIGHT)):
                if units < 3:
                    handle = make_handle(length=length, thickness=1.2)
                else:
                    handle = make_handle(length=40, thickness=1.2)
                b.add(handle)

        b.add(box)

        if units > 1:
            pad, pocket = make_cutout(
                outer_width=9.0,
                inner_width=6.0,
                depth=3.0,
                height=24.1,
            )

            sym_plane = b.Plane.XZ.offset(-WIDTH / 2)
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

        lit_cutouts(length)

    return part.part


def make_cutout_box(units: int):
    length = unit_to_length(units)

    with b.BuildPart(mode=b.Mode.PRIVATE) as part:
        with b.BuildSketch(b.Plane.XY) as sk:
            with b.BuildLine():
                b.Polyline(
                    [
                        (0, 0),
                        (0, WIDTH),
                        (length, WIDTH),
                        (length, 0),
                        ((length / 2 + 15), 0),
                        ((length / 2 + 15), 10),
                        ((length / 2 - 15), 10),
                        ((length / 2 - 15), 0),
                        (0, 0),
                    ]
                )
            b.make_face()

            vtouter = (
                sk.vertices().group_by(b.Axis.X)[0]
                + sk.vertices().group_by(b.Axis.X)[-1]
            )

            vtinner = (
                sk.vertices().group_by(b.Axis.X)[1]
                + sk.vertices().group_by(b.Axis.X)[2]
            )

            b.fillet(vtouter, radius=7)
            b.fillet(vtinner, radius=2.5)

        b.extrude(amount=HEIGHT)

        with b.BuildSketch(b.Plane.XY.offset(1.0)):
            b.add(sk)
            b.offset(amount=-WALL_DEPTH, kind=b.Kind.INTERSECTION)

        b.extrude(amount=HEIGHT, mode=b.Mode.SUBTRACT)

        with b.Locations((0.0, WIDTH, HEIGHT)):
            if units <= 3:
                b.add(make_handle(length=length, thickness=1.2))
            else:
                b.add(make_handle(length=40, thickness=1.2))
            b.extrude(sk.sketch, amount=HEIGHT, mode=b.Mode.INTERSECT)

        # Round inner edges
        b.fillet(part.edges().group_by(b.Axis.Z)[1], radius=4)

        # Bottom edge chamfer
        b.chamfer(part.edges().group_by(b.Axis.Z)[0], length=1)

        # Inner top chamfer
        b.chamfer(
            part.edges().group_by(b.Axis.Z)[-1].group_by(b.Axis.Y)[2],
            length=(WALL_DEPTH - 0.4),
        )

        pad, pocket = make_cutout(
            outer_width=9.0,
            inner_width=6.0,
            depth=3.0,
            height=24.1,
        )

        with b.Locations((OUTER_ROW_SIZE, WIDTH, 0.0)):
            locs = b.GridLocations(INNER_ROW_SIZE, 0, units - 1, 1, align=b.Align.MIN)

        for loc in locs:
            with b.Locations(loc):
                # Always add cutouts on back side
                b.add(pad, rotation=(0, 0, 180.0))
                b.add(pocket, mode=b.Mode.SUBTRACT, rotation=(0, 0, 180.0))

                # Add cutouts on front side only if they are not in the
                # box cutout area:
                if loc.position.X < (length / 2 - 15) or loc.position.X > (
                    length / 2 + 15
                ):
                    with b.Locations((0.0, -WIDTH, 0.0)):
                        b.add(pad)
                        b.add(pocket, mode=b.Mode.SUBTRACT)

        lit_cutouts(length)

    return part.part


project = Project("someline-36")


@project.model("Someline-36-U1", color=b.Color(0xFF6A13))
def u1():
    return make(units=1)


@project.model("Someline-36-U2", color=b.Color(0xFF6A13))
def u2():
    return make(units=2)


@project.model("Someline-36-U3", color=b.Color(0xFF6A13))
def u3():
    return make(units=3)


@project.model("Someline-36-U4", color=b.Color(0xFF6A13))
def u4():
    return make(units=4)


@project.model("Someline-36-U5", color=b.Color(0xFF6A13))
def u5():
    return make(units=5)


@project.model("Someline-36-U6", color=b.Color(0xFF6A13))
def u6():
    return make(units=6)


@project.model("Someline-36-U7", color=b.Color(0xFF6A13))
def u7():
    return make(units=7)


@project.model("Someline-36-U8", color=b.Color(0xFF6A13))
def u8():
    return make(units=8)


@project.model("Someline-36-U9", color=b.Color(0xFF6A13))
def u9():
    return make(units=9)


@project.model("Someline-36-U10", color=b.Color(0xFF6A13))
def u10():
    return make(units=10)


@project.model("Someline-36-C3", color=b.Color(0xFF6A13))
def c3():
    return make_cutout_box(units=3)


@project.model("Someline-36-C5", color=b.Color(0xFF6A13))
def c5():
    return make_cutout_box(units=5)


if __name__ == "__main__":
    project.main()
