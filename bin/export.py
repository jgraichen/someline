#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name
# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""
Export all root objects to STL or STEP.
"""

import argparse
import fileinput
import logging
import os
import os.path
import re
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

for path in [
    os.environ.get("PATH_TO_FREECAD_LIBDIR"),
    "~/.local/lib/freecad-python3/lib",
    "~/.local/lib/freecad/lib",
    "/usr/lib/freecad-python3/lib",
    "/usr/lib/freecad/lib",
    "/usr/local/lib/freecad-python3/lib",
    "/usr/local/lib/freecad/lib",
]:
    if path:
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            sys.path.append(path)

# pylint: disable=import-error,wrong-import-position
import FreeCAD  # noqa: E402
import Mesh  # noqa: E402
import Part  # noqa: E402

FORMAT_MESH = ["obj", "stl"]
FORMAT_PART = ["step", "wrl"]

STEP_TIMESTAMP_PATTERN = re.compile("FILE_NAME.*'(\\d+-\\d+-\\d+T\\d+:\\d+:\\d+)'")


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
            export_object(doc, root, file, fmt)


def export_object(doc, root, file, fmt):
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

    if fmt == "step":
        for line in fileinput.input(file, inplace=True):
            match = STEP_TIMESTAMP_PATTERN.match(line)
            if match:
                line = line.replace(match.group(1), "0000-00-00T00:00:00")
            print(line, end="")

    logging.info("Exported %s", file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--format", "-f", dest="formats", default=["stl"], nargs="+")
    args = parser.parse_args()

    export(args.source, args.formats)


if __name__ == "__main__":
    main()
