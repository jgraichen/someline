# pylint: disable=missing-docstring,invalid-name


from functools import partial

import build123d as b

from someline.someline import (
    make_handle,
    make_loft_box,
    make_wall_cutout,
    make_wall_cutout_pocket,
)
from someline.util import Project

WIDTH = 41.2
HEIGHT = 33.7

INNER_ROW_SIZE = 24.4  # 24.5
OUTER_ROW_SIZE = 24.4  # 24.0

WALL_DEPTH = 1.6

LIT_PIN_DY = 3.8
LIT_PIN_LENGTH = 5.25
LIT_PIN_TOPW = 3.0
LIT_PIN_BOTW = 2.0
LIT_PIN_DEPTH = 5.0


def unit_to_length(u: int):
    if u < 3:
        return u * OUTER_ROW_SIZE
    else:
        return 2 * OUTER_ROW_SIZE + (u - 2) * INNER_ROW_SIZE


def make_s36_cutouts():
    return make_wall_cutout(
        outer_width=9.0,
        inner_width=6.0,
        depth=3.0,
        height=24.1,
    )


def b_cap_hinge_cutout(length, half=False):
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
    if not half:
        with b.Locations((length - LIT_PIN_LENGTH, LIT_PIN_DY, HEIGHT)):
            b.add(cutout, mode=b.Mode.SUBTRACT)
        with b.Locations((length - LIT_PIN_LENGTH, WIDTH - LIT_PIN_DY, HEIGHT)):
            b.add(cutout, mode=b.Mode.SUBTRACT)


def make(units: int):
    length = unit_to_length(units)

    with b.BuildPart() as part:
        with make_loft_box(length, WIDTH, HEIGHT, wall_depth=WALL_DEPTH) as box:
            with b.Locations((0.0, WIDTH, HEIGHT)):
                if units < 3:
                    handle = make_handle(length=length, thickness=1.2)
                else:
                    handle = make_handle(length=50, thickness=1.2)
                b.add(handle)

            if units > 1:
                pad, pocket = make_s36_cutouts()
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

        b.add(box)
        b_cap_hinge_cutout(length)

        # The smallest U1 insets need additional cutouts as they do not
        # have enough tolerance with two 7mm rounded edges on the wall
        # separators in the Someline box.
        if units == 1:
            pocket = make_wall_cutout_pocket(
                outer_width=8.0,
                inner_width=5.0,
                depth=3.0,
                height=24.1,
            )

            with b.GridLocations(OUTER_ROW_SIZE * units, 0, 2, 1, align=b.Align.MIN):
                b.add(pocket, mode=b.Mode.SUBTRACT)

            with b.Locations((0.0, WIDTH, 0.0)):
                with b.GridLocations(
                    OUTER_ROW_SIZE * units, 0, 2, 1, align=b.Align.MIN
                ):
                    b.add(pocket, mode=b.Mode.SUBTRACT, rotation=(0.0, 0.0, 180.0))

    return part.part


def make_cutout_box(units: int):
    length = unit_to_length(units)

    with b.BuildPart(mode=b.Mode.PRIVATE) as part:
        # Sketch the base layout of the inset with a cutout on the front
        # side for where the lid hinges are in the first row. The sketch
        # already has rounded corners.
        with b.BuildSketch(b.Plane.XY) as sk:
            with b.BuildLine():
                b.Polyline(
                    [
                        (0, 0),
                        (0, WIDTH),
                        (length, WIDTH),
                        (length, 0),
                        ((length / 2 + 20), 0),
                        ((length / 2 + 20), 10),
                        ((length / 2 - 20), 10),
                        ((length / 2 - 20), 0),
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

        # Create a standard loft box based on the customized sketch. The
        # box generate will ensure the sketch is outlined into a loft
        # inset box.
        with make_loft_box(
            length,
            WIDTH,
            HEIGHT,
            wall_depth=WALL_DEPTH,
            sketch=sk.sketch,
        ) as box:
            with b.Locations((0.0, WIDTH, HEIGHT)):
                if units <= 3:
                    b.add(make_handle(length=length, thickness=1.2))
                else:
                    b.add(make_handle(length=50, thickness=1.2))
                b.extrude(sk.sketch, amount=HEIGHT, mode=b.Mode.INTERSECT)

            pad, pocket = make_s36_cutouts()

            with b.Locations((OUTER_ROW_SIZE, WIDTH, 0.0)):
                locs = b.GridLocations(
                    INNER_ROW_SIZE, 0, units - 1, 1, align=b.Align.MIN
                )

            for loc in locs:
                with b.Locations(loc):
                    # Always add wall cutouts on back side
                    b.add(pad, rotation=(0, 0, 180.0))
                    b.add(pocket, mode=b.Mode.SUBTRACT, rotation=(0, 0, 180.0))

                    # Add wall cutouts on front side only if they are not in
                    # the cutout area for the cap hinges:
                    if loc.position.X < (length / 2 - 15) or loc.position.X > (
                        length / 2 + 15
                    ):
                        with b.Locations((0.0, -WIDTH, 0.0)):
                            b.add(pad)
                            b.add(pocket, mode=b.Mode.SUBTRACT)

        b.add(box.part)
        b_cap_hinge_cutout(length)

    return part.part


def make_half_cutout_box(units: int, flip=False):
    length = unit_to_length(units) + (INNER_ROW_SIZE / 2)

    with b.BuildPart(mode=b.Mode.PRIVATE) as part:
        # Sketch the base layout of the inset with a cutout on the front
        # side for where the lid hinges are in the first row. The sketch
        # already has rounded corners.
        with b.BuildSketch(b.Plane.XY) as sk:
            with b.BuildLine():
                b.Polyline(
                    [
                        (0, 0),
                        (0, WIDTH),
                        (length, WIDTH),
                        (length, 10),
                        (length - 20, 10),
                        (length - 20, 0),
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

        # Create a standard loft box based on the customized sketch. The
        # box generate will ensure the sketch is outlined into a loft
        # inset box.
        with make_loft_box(
            length,
            WIDTH,
            HEIGHT,
            wall_depth=WALL_DEPTH,
            sketch=sk.sketch,
        ) as box:
            with b.Locations((0.0, WIDTH, HEIGHT)):
                if units <= 3:
                    b.add(make_handle(length=length, thickness=1.2))
                else:
                    b.add(make_handle(length=50, thickness=1.2))
                b.extrude(sk.sketch, amount=HEIGHT, mode=b.Mode.INTERSECT)

            pad, pocket = make_s36_cutouts()

            with b.Locations((OUTER_ROW_SIZE, WIDTH, 0.0)):
                with b.GridLocations(INNER_ROW_SIZE, 0, units, 1, align=b.Align.MIN):
                    # Always add wall cutouts on back side
                    b.add(pad, rotation=(0, 0, 180.0))
                    b.add(pocket, mode=b.Mode.SUBTRACT, rotation=(0, 0, 180.0))

            if units > 1:
                # Add one less cutout on front side
                with b.Locations((OUTER_ROW_SIZE, 0, 0.0)):
                    with b.GridLocations(
                        INNER_ROW_SIZE, 0, units - 1, 1, align=b.Align.MIN
                    ):
                        b.add(pad)
                        b.add(pocket, mode=b.Mode.SUBTRACT)

        b.add(box.part)
        b_cap_hinge_cutout(length, half=True)

        if flip:
            b.mirror(about=b.Plane.ZY, mode=b.Mode.REPLACE)

    return part.part


project = Project(
    "someline-36",
    default_color=b.Color(0xFF6A13),
    grid=(INNER_ROW_SIZE, WIDTH + 4),
)

for i in range(1, 7):
    project.add(f"U{i}", partial(make, units=i), grid=(0, i))

for i in range(7, 11):
    project.add(f"U{i}", partial(make, units=i), grid=(6, i - 6))

project.add("A1", partial(make_half_cutout_box, units=1), grid=(6, 5))
project.add("A2", partial(make_half_cutout_box, units=2), grid=(8, 5))
project.add("B1", partial(make_half_cutout_box, units=1, flip=True), grid=(13, 5))
project.add("B2", partial(make_half_cutout_box, units=2, flip=True), grid=(16, 5))
project.add("C3", partial(make_cutout_box, units=3), grid=(7, 6))
project.add("C5", partial(make_cutout_box, units=5), grid=(11, 6))


if __name__ == "__main__":
    project.main()
