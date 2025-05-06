# pylint: disable=missing-docstring


from contextlib import contextmanager

import build123d as b


@contextmanager
def make_box(
    length: float,
    width: float,
    height: float,
    wall_depth: float = 1.2,
    sketch: b.Sketch | None = None,
):
    with b.BuildPart(mode=b.Mode.PRIVATE) as part:
        b.Box(length, width, height, align=b.Align.MIN)

        with b.BuildSketch(b.Plane.XY.offset(1.0)):
            if sketch:
                b.add(sketch)
            else:
                with b.Locations((wall_depth, wall_depth)):
                    b.RectangleRounded(
                        length - (2 * wall_depth),
                        width - (2 * wall_depth),
                        align=b.Align.MIN,
                        radius=(7 - wall_depth),
                    )

        b.extrude(amount=height, mode=b.Mode.SUBTRACT)
        b.fillet(part.edges().group_by(b.Axis.Z)[1], radius=4)

        yield part

        # Curve outermost edges
        zx = part.edges().filter_by(b.Axis.Z).group_by(b.Axis.X)
        b.fillet(zx[0] + zx[-1], radius=7)

        # Bottom edge chamfer
        zy = (
            part.edges().group_by(b.Axis.Z)[0].group_by(b.Axis.Y)[0]
            + part.edges().group_by(b.Axis.Z)[0].group_by(b.Axis.Y)[-1]
        )
        b.chamfer(zy, length=1)

        # Inner top chamfer
        b.chamfer(
            part.edges().group_by(b.Axis.Z)[-1].group_by(b.Axis.Y)[1],
            length=(wall_depth - 0.4),
        )

    return part.part


@contextmanager
def make_loft_box(
    length: float,
    width: float,
    height: float,
    wall_depth: float = 1.2,
    bottom_depth: float = 1.2,
    loft: float = 0.5,
    sketch: b.Sketch | None = None,
):
    with b.BuildPart(mode=b.Mode.PRIVATE) as box:
        with b.BuildSketch(b.Plane.XY.offset(height)) as skt:
            if sketch:
                b.add(sketch)
            else:
                b.RectangleRounded(
                    width=length,
                    height=width,
                    align=b.Align.MIN,
                    radius=7,
                )
        with b.BuildSketch(b.Plane.XY) as skb:
            b.add(skt)
            b.offset(amount=-loft, kind=b.Kind.ARC)
        b.loft()

    with b.BuildPart(mode=b.Mode.PRIVATE) as part:
        b.add(box)
        b.offset(
            amount=-wall_depth,
            openings=part.faces().group_by(b.Axis.Z)[-1]
            + part.faces().group_by(b.Axis.Z)[0],
        )
        b.extrude(skb.sketch, amount=bottom_depth)

        # Round inner bottom edges
        b.fillet(part.edges().group_by(b.Axis.Z)[1], radius=4)

        yield part

        # Cutoff excess stuff
        b.add(box, mode=b.Mode.INTERSECT)

        # Bottom edge chamfer
        zy = (
            part.edges().group_by(b.Axis.Z)[0].group_by(b.Axis.Y)[0]
            + part.edges().group_by(b.Axis.Z)[0].group_by(b.Axis.Y)[-1]
        )
        b.chamfer(zy, length=1)

        # Inner top chamfer
        b.chamfer(
            part.edges().group_by(b.Axis.Z)[-1].group_by(b.Axis.X)[1],
            length=(wall_depth - 0.4),
        )

    return part.part


def make_handle(length: float, thickness=0.8):
    with b.BuildPart(mode=b.Mode.PRIVATE) as handle:
        with b.BuildSketch(b.Plane.YZ):
            with b.BuildLine():
                b.Polyline(
                    [
                        (0, 0),
                        (0, -9 - thickness),
                        (-7, -thickness),
                        (-7, 0),
                        (0, 0),
                    ]
                )
            b.make_face()
        b.extrude(amount=length)
    return handle.part


def make_wall_cutout(
    outer_width: float,
    inner_width: float,
    depth: float,
    height: float,
    wall: float = 0.8,
):
    pocket = make_wall_cutout_pocket(
        outer_width=outer_width,
        inner_width=inner_width,
        depth=depth,
        height=height,
    )

    with b.BuildPart(mode=b.Mode.PRIVATE) as pad:
        b.add(pocket)

        front_face = pad.faces().sort_by(b.Axis.Y)[0]
        bottom_face = pad.faces().sort_by(b.Axis.Z)[0]
        b.offset(
            amount=wall, kind=b.Kind.INTERSECTION, openings=[front_face, bottom_face]
        )
        b.Box(
            outer_width + wall * 3,
            depth + wall * 2,
            1.0,
            align=(b.Align.CENTER, b.Align.MIN, b.Align.MIN),
            mode=b.Mode.SUBTRACT,
        )
        b.fillet(pad.edges().filter_by(b.Axis.Z).group_by(b.Axis.Y)[-1], radius=wall)

    return (pad.part, pocket)


def make_wall_cutout_pocket(
    outer_width: float,
    inner_width: float,
    depth: float,
    height: float,
):
    with b.BuildPart(mode=b.Mode.PRIVATE) as pocket:
        with b.BuildSketch(b.Plane.XY):
            with b.BuildLine():
                b.Polyline(
                    [
                        (-(outer_width / 2), 0.0),
                        (-(inner_width / 2), depth),
                        (+(inner_width / 2), depth),
                        (+(outer_width / 2), 0.0),
                        (-(outer_width / 2), 0.0),
                    ]
                )
            b.make_face()

        b.extrude(amount=height + depth)
        b.chamfer(
            pocket.edges().group_by(b.Axis.Z)[-1].group_by(b.Axis.Y)[-1],
            length=(depth - 0.001),
        )

    return pocket.part
