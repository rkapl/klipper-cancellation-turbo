#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import pathlib
import re
import shutil
import enum
import sys
import tempfile
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, TypeVar
from preprocess_cancellation_cext import Hull, Point, GCodeParser

__version__ = "0.2.0"


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("prepropress_cancellation")

shapely = None
try:
    import shapely.geometry
    import numpy
except ImportError:
    logger.info("Shapely not found, complex hulls disabled")
except OSError:
    logger.exception("Failed to import shapely. Are you missing libgeos?")

HEADER_MARKER = f"; Pre-Processed for Cancel-Object support by preprocess_cancellation v{__version__}\n"

PathLike = TypeVar("PathLike", str, pathlib.Path)

class KnownObject(NamedTuple):
    name: str
    hull: Hull

def _clean_id(id):
    return re.sub(r"\W+", "_", id).strip("_")


def parse_gcode(line):
    # drop comments
    line = line.split(";", maxsplit=1)[0]
    command, *params = line.strip().split()
    parsed = {}
    for param in params:
        if "=" in param:
            parsed.update(dict(zip(param.split("=", maxsplit=1))))
        else:
            parsed.update({param[0].upper(): param[1:]})
    return command, parsed


def header(object_count):
    yield "\n\n"
    yield HEADER_MARKER
    yield f"; {object_count} known objects\n"


def define_object(
    name,
    center: Optional[Point] = None,
    polygon: Optional[Point] = None,
):
    yield f"EXCLUDE_OBJECT_DEFINE NAME={name}"
    if center:
        yield f" CENTER={center.x:0.3f},{center.y:0.3f}"
    if polygon:
        yield f" POLYGON={json.dumps([[p.x, p.y] for p in polygon])}"
    yield "\n"


def object_start_marker(object_name):
    yield f"EXCLUDE_OBJECT_START NAME={object_name}\n"


def object_end_marker(object_name):
    yield f"EXCLUDE_OBJECT_END NAME={object_name}\n"

class SlicerProcessor:
    known_objects: Dict[str, KnownObject]
    interest_map: Dict[int, function]
    def __init__(self):
        self.known_objects = {}
        self.interest_map = {}
        self.parser = GCodeParser()
        self.current_object_id = None

    def register_interest(self, line, callback):
        id = len(self.interest_map) + 1
        self.parser.register_interest(line, id)
        self.interest_map[id] = callback
        
    # Registers interesting lines for the first stage where we scan for objects and their boundaries
    def slicer_start_scan(self):
        pass

    # Registers interesting lines for the second stage where we replace slicer markers by klipper markers
    def slicer_start_output(self):
        pass

    def slicer_header(self):
        return []

    def define_object_id(self, object_id: str, name: str = None):
        if name is None:
            name = object_id
        if object_id not in self.known_objects:
            h = Hull()
            h.precision = 1
            self.known_objects[object_id] = KnownObject(_clean_id(name), h)
        return self.known_objects[object_id].hull

    def start_object_id(self, object_id: str, name: str = None):
        self.parser.hull = self.define_object_id(object_id, name=name)

    def stop_object(self):
        self.parser.hull = None

    def get_hull_bounds(self, hull):
        if shapely:
            points_array = numpy.frombuffer(hull.point_bytes())
            points_array.shape = (points_array.size // 2, 2)
            points = shapely.MultiPoint(points_array)
            hull = points.convex_hull
            #print(len(hull.exterior.coords))
            center = hull.centroid
            bb = [Point(x,y) for x,y in hull.exterior.coords]
        else:
            xmin, ymin, xmax, ymax = hull.bounding_box()
            center = Point((xmax + xmin) / 2, (ymax + ymin) / 2)
            bb = [
                Point(xmin, ymin),
                Point(xmin, ymax),
                Point(xmax, ymax),
                Point(xmax, ymin),
            ]
        return center, bb

    def output_object_definitions(self):
        yield from header(len(self.known_objects))
        for object_id, hull in self.known_objects.values():
            center, polygon = self.get_hull_bounds(hull)
            yield from define_object(
                object_id,
                center=center,
                polygon=polygon,
            )

    def output_object_start(self, id):
        if self.current_object_id is not None:
            yield from self.output_object_end()

        self.current_object_id = id
        yield from object_start_marker(self.known_objects[id].name)
    
    def output_object_end(self):
        yield from object_end_marker(self.known_objects[self.current_object_id].name)
        self.current_object_id = None

class SlicerSlic3rFamily(SlicerProcessor):
    @staticmethod
    def _get_id(line):
        return line.split("printing object")[1].strip()

    def slicer_start_scan(self):
        self.register_interest('; printing object ', 
            lambda line: self.start_object_id(SlicerSlic3rFamily._get_id(line)))
        self.register_interest('; stop printing object ',lambda _: self.stop_object())

    def slicer_start_output(self):
        self.register_interest('; printing object ', 
            lambda line: self.output_object_start(SlicerSlic3rFamily._get_id(line)))
        self.register_interest('; stop printing object ', lambda _: self.output_object_end())

    def slicer_header(self):
        yield from self.output_object_definitions()

class SlicerCura(SlicerProcessor):
    last_time_elapsed: str

    def _scan_elapsed(self, line):
        self.last_time_elapsed = line

    def _scan_mesh(self, line):
        object_name = line.split(":", maxsplit=1)[1].strip()
        if object_name == 'NONMESH':
            return
        self.start_object_id(object_name)

    def slicer_start_scan(self):
        self.last_time_elapsed = None

        self.register_interest(';MESH', self._scan_mesh)
        self.register_interest(';TIME_ELAPSED:', self._scan_elapsed)

    def slicer_header(self):
        yield from self.output_object_definitions()

    def _output_mesh(self, line):
        object_name = line.split(":", maxsplit=1)[1].strip()
        if object_name == 'NONMESH':
            return []
        yield from self.output_object_start(object_name)

    def _output_elapsed(self, line):
        if self.last_time_elapsed == line and self.current_object_id:
            self.output_object_end()

    def slicer_start_output(self):
        self.register_interest(';MESH', self._output_mesh)
        self.register_interest(';TIME_ELAPSED:', self._output_elapsed)

class SlicerIdeamaker(SlicerProcessor):
    def _scan_printing(self, line):
        self.ideamaker_object_name = line.split(":")[1].strip()

    def _scan_printing_id(self, line):
        id = line.split(":")[1].strip()
        # Ignore the internal non-object meshes
        if id == "-1":
            return
        self.start_object_id(id, name=self.ideamaker_object_name)

    def slicer_start_scan(self):
        self.ideamaker_object_name = "unknown"
        self.register_interest(';PRINTING:', self._scan_printing)
        self.register_interest(';PRINTING_ID:', self._scan_printing_id)

        # This one is funnier
        # theres blocks like this, we can grab all these to get the names and ideamaker's IDs for them.
        #   ;PRINTING: test_bed_part0.3mf
        #   ;PRINTING_ID: 0

    def _output_printing_id(self, line):
        printing_id = line.split(":")[1].strip()
        if printing_id == "-1":
            return
        yield from self.output_object_start(printing_id)

    def _output_end(self, line):
        if self.current_object_id is not None:
            yield from self.output_object_end()

    def slicer_start_output(self):
        self.register_interest(';TOTAL_NUM:', lambda _: self.output_object_definitions())
        self.register_interest(';PRINTING_ID:', self._output_printing_id)
        self.register_interest(';REMAINING_TIME: 0', self._output_end)

class SlicerM486(SlicerProcessor):
    def _scan_m486(self, line):
        _, params = parse_gcode(line)
        if "T" in params:
            for i in range(-1, int(params["T"])):
                self.define_object_id(str(i))

        elif "S" in params:
            self.start_object_id(params["S"])

    def _output_m486(self, line):
        _, params = parse_gcode(line)
        if "T" in params:
            del self.known_objects["-1"]
            yield from self.output_object_definitions()
        elif "S" in params:
            if params["S"] != "-1":
                yield from self.output_object_start(params["S"])

        yield '; ' + line

    def slicer_start_scan(self):
        self.register_interest('M486', self._scan_m486)

    def slicer_start_output(self):
        self.register_interest('M486', self._output_m486)

# Note:
#   Slic3r:     does not output any markers into GCode
#   Kisslicer:  does not output any markers into GCode
#   Kiri:Moto:  does not output any markers into GCode
#   Simplify3D: I was unable to figure out multiple processes
SLICERS: dict[str, Tuple[str, callable]] = {
    "superslicer": ("; generated by SuperSlicer", SlicerSlic3rFamily),
    "prusaslicer": ("; generated by PrusaSlicer", SlicerSlic3rFamily),
    "slic3r": ("; generated by Slic3r", SlicerSlic3rFamily),
    "cura": (";Generated with Cura_SteamEngine", SlicerCura),
    "ideamaker": (";Sliced by ideaMaker", SlicerIdeamaker),
    "m486": ("M486", SlicerM486),
}


def identify_slicer_marker(line):
    for name, (marker, processor) in SLICERS.items():
        if line.strip().startswith(marker):
            logger.debug("Identified slicer %s", name)
            return processor

def _process_lines(infile, slicer_factory):
    slicer: SlicerProcessor = slicer_factory()

    # Identify objects
    infile.seek(0)
    slicer.slicer_start_scan()
    for line in infile:
        r = slicer.parser.feed_line(line) 
        if r is not None:
            slicer.interest_map[r](line)


    # Replacement & Output
    slicer.interest_map = {}
    slicer.parser.hull = None
    slicer.parser.clear_interests()
    slicer.slicer_start_output()
    infile.seek(0)

    yield from slicer.slicer_header()
    for line in infile:
        r = slicer.parser.feed_line(line) 
        if r is not None:
            more = slicer.interest_map[r](line)
            if more is not None:
                yield from more
        else:
            yield line

    if slicer.current_object_id is not None:
        yield from slicer.output_object_end()

# These methods are for compatibility with Moonraker and other API users
def preprocess_pipe(infile):
    yield from infile

def preprocess_slicer(infile):
    yield from _process_lines(infile, slicer_factory=SlicerSlic3rFamily)

def preprocess_cura(infile):
    yield from _process_lines(infile, slicer_factory=SlicerCura)

def preprocess_ideamaker(infile):
    yield from _process_lines(infile, slicer_factory=SlicerIdeamaker)

def preprocess_m486(infile):
    yield from _process_lines(infile, slicer_factory=SlicerM486)

def preprocessor(infile, outfile, slicer_factory=None):
    I_PROCESSED = 1
    I_SLICER_MARKER = 2
    parser = GCodeParser()

    # Stage 1, identify slicers
    if slicer_factory is None:
        logger.debug("Identifying slicer")
        parser.register_interest('EXCLUDE_OBJECT_DEFINE', I_PROCESSED)
        parser.register_interest('DEFINE_OBJECT', I_PROCESSED)
        for marker, _ in SLICERS.values():
            parser.register_interest(marker, I_SLICER_MARKER)

        for line in infile:
            interest = parser.feed_line(line)
            if interest is None:
                continue

            if interest == I_PROCESSED:
                logger.info("GCode already supports cancellation")
                infile.seek(0)
                outfile.write(infile.read())
                return True
            elif interest == I_SLICER_MARKER:
                slicer_factory = identify_slicer_marker(line)

    if slicer_factory is None:
        logger.warn("Could not identify slicer")
        return False

    # Stage 2, output & replacement
    for line in _process_lines(infile, slicer_factory):
        outfile.write(line)

    return True

def process_file_for_cancellation(filename: PathLike, output_suffix=None) -> int:
    filepath = pathlib.Path(filename)
    outfilepath = filepath

    if output_suffix:
        outfilepath = outfilepath.with_name(outfilepath.stem + output_suffix + outfilepath.suffix)

    tempfilepath = pathlib.Path(tempfile.mktemp())

    with filepath.open("r") as fin:
        with tempfilepath.open("w") as fout:
            res = preprocessor(fin, fout)

    if res:
        if outfilepath.exists():
            outfilepath.unlink()
        shutil.move(tempfilepath, outfilepath)

    else:
        tempfilepath.unlink()

    return res


def _main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--output-suffix",
        "-o",
        help="Add a suffix to gcoode output. Without this, gcode will be rewritten in place",
    )
    argparser.add_argument(
        "--disable-shapely", help="Disable using shapely to generate a hull polygon for objects", action="store_true"
    )
    argparser.add_argument("gcode", nargs="*")

    exitcode = 0

    args = argparser.parse_args()
    if args.disable_shapely:
        global shapely
        shapely = None

    for filename in args.gcode:
        if not process_file_for_cancellation(filename, args.output_suffix):
            exitcode = 1

    sys.exit(exitcode)


if __name__ == "__main__":
    _main()
