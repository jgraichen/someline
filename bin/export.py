#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name
# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""
Export all root objects to STL or STEP.
"""

import argparse
import logging
import os
import os.path
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

for path in [
    os.environ["PATH_TO_FREECAD_LIBDIR"],
    "~/.local/lib/freecad-python3/lib",
    "~/.local/lib/freecad/lib",
    "/usr/lib/freecad-python3/lib",
    "/usr/lib/freecad/lib",
    "/usr/local/lib/freecad-python3/lib",
    "/usr/local/lib/freecad/lib",
]:
    path = os.path.expanduser(path)
    if os.path.isdir(path):
        sys.path.append(path)

# pylint: disable=import-error,wrong-import-position
import FreeCAD  # noqa: E402
import Mesh  # noqa: E402
import Part  # noqa: E402

FORMAT_MESH = ["obj", "stl"]
FORMAT_PART = ["step", "wrl"]


def export(
    source: str,
    formats: list[str],
):
    output = os.path.join(os.path.dirname(source), "export")
    os.makedirs(output, exist_ok=True)

    name, _ = os.path.splitext(os.path.basename(source))
    doc = FreeCAD.openDocument(source)

    for root in doc.RootObjects:
        for fmt in formats:
            file = os.path.join(output, f"{name}-{root.Label}.{fmt}")

            if fmt.lower() in FORMAT_MESH:
                Mesh.export([root], file)

            else:
                if root.isDerivedFrom("Part::Feature"):
                    # Root is a part body: We can directly export that
                    objects = [root]

                elif root.isDerivedFrom("App::Part"):
                    # Root is an assembly: Scan for all individual parts
                    objects = doc.Objects
                    objects = [o for o in objects if root in o.InListRecursive]

                Part.export(objects, file)

            logging.info("Exported %s", file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--format", "-f", dest="formats", default=["stl"], nargs="+")
    args = parser.parse_args()

    export(args.source, args.formats)


if __name__ == "__main__":
    main()
