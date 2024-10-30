# pylint: disable=missing-docstring


from contextlib import contextmanager

import build123d as b


@contextmanager
def make_box(length: float, width: float, height: float):
    with b.BuildPart(mode=b.Mode.PRIVATE) as part:
        b.Box(length, width, height, align=False)

        with b.BuildSketch(b.Plane.XY.offset(1.0)):
            with b.Locations((1.2, 1.2)):
                b.RectangleRounded(
                    length - 2.4,
                    width - 2.4,
                    align=b.Align.MIN,
                    radius=5.8,
                )

        b.extrude(amount=height, mode=b.Mode.SUBTRACT)
        b.fillet(part.edges().group_by(b.Axis.Z)[1], radius=4)

        yield part

        # Curve outermost edges
        zx = part.edges().filter_by(b.Axis.Z).group_by(b.Axis.Y)
        b.fillet(zx[0] + zx[-1], radius=7)

        # Bottom edge chamfer
        b.chamfer(part.edges().group_by(b.Axis.Z)[0], length=1)

        # Inner top chamfer
        b.chamfer(
            part.edges().group_by(b.Axis.Z)[-1].group_by(b.Axis.Y)[1],
            length=0.8,
        )

    return part.part


def make_handle(length: float):
    with b.BuildPart(mode=b.Mode.PRIVATE) as handle:
        with b.BuildSketch(b.Plane.YZ):
            with b.BuildLine():
                b.Polyline(
                    [
                        (0, 0),
                        (0, -9),
                        (-7, -0.8),
                        (-7, 0),
                        (0, 0),
                    ]
                )
            b.make_face()
        b.extrude(amount=length)
    return handle.part


def make_cutout(
    outer_width: float,
    inner_width: float,
    depth: float,
    height: float,
    wall: float = 0.8,
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

    return (pad.part, pocket.part)
