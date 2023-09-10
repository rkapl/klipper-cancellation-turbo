import dataclasses
import json
import pathlib
import re
import subprocess
import sys

import pytest

from preprocess_cancellation import preprocess_cura, preprocess_ideamaker, preprocess_m486, preprocess_slicer
import preprocess_cancellation
from test_preprocessor import collect_definitions

try:
    import shapely
except ImportError:
    pytest.skip("Requires shapely installed", allow_module_level=True)


gcode_path = pathlib.Path("./GCode")


def test_cli():
    """
    Ensure the preprocesor does not crash
    """
    try:
        command = [
            sys.executable,
            "./preprocess_cancellation.py",
            "-o",
            ".testing",
            *gcode_path.glob("*.gcode"),
        ]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            proc.wait()
            assert proc.returncode == 0
    finally:
        for testing_file in gcode_path.glob("*.testing.gcode"):
            testing_file.unlink()

@dataclasses.dataclass
class Def:
    name: str
    center: tuple
    polygon: list[list]

def parse_definitions(definitions) -> dict[str, Def]:
    dd = {}
    for d in definitions:
        parts = d.split(' ')
        if parts[0] != 'EXCLUDE_OBJECT_DEFINE':
            continue
        params = dict(p.split('=', maxsplit=1) for p in parts[1:])

        r = Def(params['NAME'], 
            [float(v) for v in params['CENTER'].split(',')], 
            json.loads(params['POLYGON'])
        )
        dd[r.name] = r
    return dd

def check_def(definitions, id, center, polygon):
    assert id in definitions
    d = definitions[id]
    assert d.center == center
    assert d.polygon == polygon

def test_m486():
    global precision
    preprocess_cancellation.precision = 0.00001
    with (gcode_path / "m486.gcode").open("r") as f:
        results = "".join(list(preprocess_m486(f))).split("\n")

    definitions = parse_definitions(results)

    check_def(definitions, '0',
        [160.273, 148.578],
        [[160.513,146.681],[160.268,146.693],[159.931,146.769],[158.514,147.252],[158.179,148.01],[158.103,148.462],[158.127,148.938],[158.245,149.4],[158.392,149.726],[159.679,150.294],[160.055,150.429],[160.475,150.479],[161.126,150.446],[161.461,150.301],[161.846,149.914],[162.077,149.631],[162.233,149.348],[162.342,149.02],[162.392,148.641],[162.371,148.283],[162.222,147.623],[161.633,147.062],[161.313,146.869],[161.128,146.798],[160.938,146.734],[160.513,146.681]]
    )

    check_def(definitions, '1',
        [150.49,155.505],
        [[148.11,153.105],[148.11,157.895],[152.9,157.895],[152.84,153.105],[148.11,153.105]]
    )

    check_def(definitions, '2',
        [139.505, 155.5],
        [[137.11,153.105],[137.11,157.895],[141.9,157.895],[141.9,153.105],[137.11,153.105]]
    )

    check_def(definitions, '3',
        [144.505, 144.5],
        [[137.11,142.105],[137.11,146.895],[151.9,146.895],[151.9,142.105],[137.11,142.105]]
    )

    assert results.count(f"EXCLUDE_OBJECT_START NAME=0") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=0") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=1") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=1") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=2") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=2") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=3") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=3") == 25


def test_superslicer():
    global precision
    preprocess_cancellation.precision = 0.00001

    with (gcode_path / "superslicer.gcode").open("r") as f:
        results = "".join(list(preprocess_slicer(f))).split("\n")

    definitions = parse_definitions(results)

    check_def(definitions, 'cube_1_id_0_copy_0',
        [150.49, 155.505],
        [[148.215,153.21],[148.215,157.79],[152.795,157.79],[152.735,153.21],[148.215,153.21]]
    )

    check_def(definitions, 'cube_1_id_0_copy_1',
        [139.505, 155.5],
        [[137.215,153.21],[137.215,157.79],[141.795,157.79],[141.795,153.21],[137.215,153.21]]
    )

    check_def(definitions, 'union_3_id_2_copy_0',
        [144.505, 144.5],
        [[137.215,142.21],[137.215,146.79],[151.795,146.79],[151.795,142.21],[137.215,142.21]]
    )

    check_def(definitions, 'cylinder_2_id_1_copy_0',
        [160.418, 148.591],
        [[160.207,146.625],[159.764,146.745],[159.4,146.942],[158.346,147.789],[158.23,148.24],[158.205,148.581],[158.567,149.29],[158.862,149.692],[159.422,150.245],[159.661,150.425],[160.384,150.734],[161.201,150.427],[161.569,150.234],[161.88,149.983],[162.134,149.676],[162.327,149.307],[162.448,148.866],[162.447,147.931],[162.117,147.477],[161.561,146.927],[161.243,146.695],[160.207,146.625]]
    )


def test_prusaslicer():
    global precision
    preprocess_cancellation.precision = 0.00001
    with (gcode_path / "prusaslicer.gcode").open("r") as f:
        results = "".join(list(preprocess_slicer(f))).split("\n")

    definitions = parse_definitions(results)

    check_def(definitions, 'cylinder_2_id_1_copy_0',
        [160.273, 148.578],
        [[160.513,146.681],[160.268,146.693],[159.931,146.769],[158.514,147.252],[158.179,148.01],[158.103,148.462],[158.127,148.938],[158.245,149.4],[158.392,149.726],[159.679,150.294],[160.055,150.429],[160.475,150.479],[161.126,150.446],[161.461,150.301],[161.846,149.914],[162.077,149.631],[162.233,149.348],[162.342,149.02],[162.392,148.641],[162.371,148.283],[162.222,147.623],[161.633,147.062],[161.313,146.869],[161.128,146.798],[160.938,146.734],[160.513,146.681]],
    )

    check_def(definitions, 'cube_1_id_0_copy_0',
         [150.49, 155.505],
        [[148.11,153.105],[148.11,157.895],[152.9,157.895],[152.84,153.105],[148.11,153.105]]
    )

    check_def(definitions, 'cube_1_id_0_copy_1',
        [139.505, 155.5],
        [[137.11,153.105],[137.11,157.895],[141.9,157.895],[141.9,153.105],[137.11,153.105]]
    )

    check_def(definitions, 'union_3_id_2_copy_0',
        [144.505, 144.5],
        [[137.11,142.105],[137.11,146.895],[151.9,146.895],[151.9,142.105],[137.11,142.105]]
    )

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cylinder_2_id_1_copy_0") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cylinder_2_id_1_copy_0") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cube_1_id_0_copy_0") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cube_1_id_0_copy_0") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cube_1_id_0_copy_1") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cube_1_id_0_copy_1") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=union_3_id_2_copy_0") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=union_3_id_2_copy_0") == 25


def test_slic3r():
    global precision
    preprocess_cancellation.precision = 0.00001
    with (gcode_path / "slic3r.gcode").open("r") as f:
        results = "".join(list(preprocess_slicer(f))).split("\n")

    definitions = parse_definitions(results)

    check_def(definitions, 'cube_1_stl_id_0_copy_0',
        [99.995, 83.485],
        [[97.72,81.22],[97.72,85.78],[102.28,85.72],[102.28,81.22],[97.72,81.22]]
    )

    check_def(definitions, 'cube_1_stl_id_0_copy_1',
        [99.995, 116.485],
        [[97.72,114.22],[97.72,118.78],[102.28,118.72],[102.28,114.22],[97.72,114.22]]
    )

    check_def(definitions, 'cylinder_2_stl_id_1_copy_0',
        [100.0, 94.5],
        [[100.17,92.227],[99.717,92.239],[99.271,92.34],[98.963,92.471],[98.579,92.718],[98.254,93.035],[97.999,93.41],[97.822,93.828],[97.732,94.273],[97.732,94.727],[97.822,95.172],[97.999,95.59],[98.254,95.965],[98.579,96.282],[98.96,96.528],[99.383,96.694],[99.83,96.773],[100.283,96.761],[100.726,96.66],[101.139,96.474],[101.51,96.207],[101.744,95.967],[102.001,95.59],[102.178,95.172],[102.268,94.727],[102.268,94.273],[102.178,93.828],[102.001,93.41],[101.746,93.035],[101.421,92.718],[101.04,92.472],[100.617,92.306],[100.17,92.227]]
    )

    check_def(definitions, 'union_3_stl_id_2_copy_0',
        [100.0, 105.5],
        [[92.72,103.22],[92.72,107.78],[107.28,107.78],[107.28,103.22],[92.72,103.22]]
    )

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cube_1_stl_id_0_copy_0") == 16
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cube_1_stl_id_0_copy_0") == 16

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cube_1_stl_id_0_copy_1") == 16
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cube_1_stl_id_0_copy_1") == 16

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cylinder_2_stl_id_1_copy_0") == 16
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cylinder_2_stl_id_1_copy_0") == 16

    assert results.count(f"EXCLUDE_OBJECT_START NAME=union_3_stl_id_2_copy_0") == 16
    assert results.count(f"EXCLUDE_OBJECT_END NAME=union_3_stl_id_2_copy_0") == 16


def test_cura():
    global precision
    preprocess_cancellation.precision = 0.00001
    with (gcode_path / "cura.gcode").open("r") as f:
        results = "".join(list(preprocess_cura(f))).split("\n")

    definitions = parse_definitions(results)

    check_def(definitions, 'cylinder_2_stl',
        [143.5, 143.5],
        [[143.448,141.201],[142.992,141.257],[142.559,141.401],[142.182,141.615],[141.888,141.858],[141.597,142.207],[141.379,142.608],[141.245,143.047],[141.2,143.507],[141.24,143.926],[141.379,144.392],[141.588,144.779],[141.898,145.151],[142.247,145.429],[142.664,145.643],[143.095,145.764],[143.552,145.799],[144.009,145.743],[144.441,145.599],[144.845,145.366],[145.166,145.086],[145.402,144.794],[145.623,144.387],[145.755,143.953],[145.8,143.494],[145.753,143.038],[145.623,142.613],[145.409,142.216],[145.101,141.848],[144.753,141.571],[144.36,141.367],[143.905,141.236],[143.448,141.201]]
    )

    check_def(definitions, 'cube_1_stl',
        [150.0, 143.5],
        [[147.7,141.2],[147.7,145.8],[152.3,145.8],[152.3,141.2],[147.7,141.2]]
    )

    check_def(definitions, 'union_3_stl',
        [150.0, 150.0],
        [[142.7,147.7],[142.7,152.3],[157.3,152.3],[157.3,147.7],[142.7,147.7]]
    )

    check_def(definitions, 'cube_1_stl_1',
        [149.994, 153.664],
        [[150.719,147.305],[150.569,147.309],[148.861,148.051],[148.4,148.513],[147.7,154.17],[147.7,158.77],[152.3,158.77],[152.3,154.17],[151.494,148.693],[151.255,147.686],[150.719,147.305]]
    )

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cylinder_2_stl") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cylinder_2_stl") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cube_1_stl") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cube_1_stl") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=union_3_stl") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=union_3_stl") == 25

    assert results.count(f"EXCLUDE_OBJECT_START NAME=cube_1_stl_1") == 25
    assert results.count(f"EXCLUDE_OBJECT_END NAME=cube_1_stl_1") == 25


def test_ideamaker():
    global precision
    preprocess_cancellation.precision = 0.00001
    with (gcode_path / "ideamaker.gcode").open("r") as f:
        results = "".join(list(preprocess_ideamaker(f))).split("\n")

    definitions = parse_definitions(results)
    
    check_def(definitions, 'test_bed_part1_3mf',
        [112.0, 102.5],
        [[111.998,100.194],[111.545,100.239],[111.107,100.375],[110.705,100.594],[110.356,100.887],[110.068,101.248],[109.878,101.611],[109.755,101.998],[109.701,102.49],[109.735,102.901],[109.859,103.343],[110.068,103.752],[110.35,104.107],[110.709,104.409],[111.107,104.625],[111.544,104.761],[112.002,104.806],[112.455,104.761],[112.893,104.625],[113.295,104.406],[113.644,104.113],[113.918,103.773],[114.109,103.421],[114.244,103.005],[114.299,102.51],[114.265,102.099],[114.141,101.657],[113.932,101.248],[113.65,100.893],[113.298,100.596],[112.893,100.375],[112.47,100.242],[111.998,100.194]]
    )

    check_def(definitions, 'test_bed_part2_3mf',
        [89.001, 102.5],
        [[81.701,100.194],[81.701,104.806],[96.301,104.806],[96.301,100.194],[81.701,100.194]]
    )

    check_def(definitions, 'test_bed_part0_3mf',
        [103.001, 102.5],
        [[100.701,100.194],[100.701,104.806],[105.301,104.806],[105.301,100.194],[100.701,100.194]]
    )

    check_def(definitions, 'test_bed_part0_1_3mf',
        [120.999, 102.5],
        [[118.699,100.194],[118.699,104.806],[123.299,104.806],[123.299,100.194],[118.699,100.194]]
    )

    assert results.count("EXCLUDE_OBJECT_START NAME=test_bed_part1_3mf") == 32
    assert results.count("EXCLUDE_OBJECT_END NAME=test_bed_part1_3mf") == 32

    assert results.count("EXCLUDE_OBJECT_START NAME=test_bed_part2_3mf") == 32
    assert results.count("EXCLUDE_OBJECT_END NAME=test_bed_part2_3mf") == 32

    assert results.count("EXCLUDE_OBJECT_START NAME=test_bed_part0_3mf") == 33
    assert results.count("EXCLUDE_OBJECT_END NAME=test_bed_part0_3mf") == 33

    assert results.count("EXCLUDE_OBJECT_START NAME=test_bed_part0_1_3mf") == 33
    assert results.count("EXCLUDE_OBJECT_END NAME=test_bed_part0_1_3mf") == 33


def test_issue_1_prusaslicer_point_collection():
    global precision
    preprocess_cancellation.precision = 0.00001

    with (gcode_path / "prusaslicer-issue1.gcode").open("r") as f:
        results = "".join(list(preprocess_slicer(f))).split("\n")

    definitions = parse_definitions(results)
    
    check_def(definitions, 'Shape_Cylinder_id_1_copy_0',
        [155.01, 108.563],
        [[155.012,94.688],[153.801,94.741],[152.362,94.943],[151.141,95.238],[149.812,95.698],[148.495,96.312],[147.318,97.015],[146.278,97.78],[145.199,98.752],[144.247,99.806],[143.437,100.909],[142.759,102.049],[142.145,103.365],[141.675,104.728],[141.39,105.914],[141.189,107.337],[141.135,108.562],[141.202,109.923],[141.39,111.211],[141.672,112.387],[142.145,113.761],[142.759,115.077],[143.468,116.263],[144.227,117.295],[145.199,118.374],[146.273,119.342],[147.251,120.066],[148.496,120.814],[149.774,121.412],[151.106,121.877],[152.362,122.183],[153.787,122.384],[155.009,122.438],[156.409,122.367],[157.658,122.183],[158.999,121.852],[160.208,121.427],[161.524,120.814],[162.707,120.107],[163.742,119.346],[164.821,118.374],[165.742,117.357],[166.513,116.322],[167.261,115.077],[167.863,113.79],[168.321,112.478],[168.63,111.211],[168.827,109.831],[168.885,108.564],[168.818,107.202],[168.63,105.914],[168.348,104.738],[167.875,103.365],[167.261,102.048],[166.548,100.856],[165.793,99.831],[164.821,98.752],[163.744,97.781],[162.77,97.06],[161.737,96.427],[160.431,95.79],[159.299,95.367],[157.895,94.991],[156.46,94.764],[155.012,94.688]]
    )

    check_def(definitions, 'Shape_Box_id_0_copy_0',
        [106.865, 107.537],
        [[94.59,95.262],[94.59,119.812],[119.14,119.812],[119.14,95.262],[94.59,95.262]]
    )

    assert results.count(f"EXCLUDE_OBJECT_START NAME=Shape_Cylinder_id_1_copy_0") == 125
    assert results.count(f"EXCLUDE_OBJECT_END NAME=Shape_Cylinder_id_1_copy_0") == 125

    assert results.count(f"EXCLUDE_OBJECT_START NAME=Shape_Box_id_0_copy_0") == 125
    assert results.count(f"EXCLUDE_OBJECT_END NAME=Shape_Box_id_0_copy_0") == 125


def test_issue_2_retractions_included_in_bounding_boxes():
    global precision
    preprocess_cancellation.precision = 0.1

    with (gcode_path / "regressions" / "issue_2_retractions.gcode").open("r") as f:
        results = "".join(list(preprocess_slicer(f))).split("\n")

    definitions = parse_definitions(results)

    if False:
        for d in definitions.values():
            print(f'    check_def(definitions, \'{d.name}\', ')
            print(f'       {json.dumps(d.center)},'),
            print(f'       {json.dumps(d.polygon)}'),
            print(f'    )')


    check_def(definitions, 'Leaf_stl_id_0_copy_0', 
       [262.55, 252.95],
       [[248.5, 217.6], [247.6, 218.5], [247.6, 287.4], [248.5, 288.3], [276.6, 288.3], [277.5, 287.4], [277.5, 218.5], [276.6, 217.6], [248.5, 217.6]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_17', 
       [210.951, 263.75],
       [[176.5, 248.8], [175.6, 249.7], [175.6, 277.8], [176.5, 278.7], [245.5, 278.7], [246.3, 277.8], [246.3, 249.7], [245.5, 248.8], [176.5, 248.8]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_7', 
       [210.951, 232.55],
       [[176.5, 217.6], [175.6, 218.5], [175.6, 246.6], [176.5, 247.5], [245.5, 247.5], [246.3, 246.6], [246.3, 218.5], [245.5, 217.6], [176.5, 217.6]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_3', 
       [210.951, 201.35],
       [[176.5, 186.4], [175.6, 187.3], [175.6, 215.4], [176.5, 216.3], [245.5, 216.3], [246.3, 215.4], [246.3, 187.3], [245.5, 186.4], [176.5, 186.4]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_2', 
       [210.951, 170.151],
       [[176.5, 155.2], [175.6, 156.1], [175.6, 184.3], [176.5, 185.1], [245.5, 185.1], [246.3, 184.3], [246.3, 156.1], [245.5, 155.2], [176.5, 155.2]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_5', 
       [210.951, 139.049],
       [[176.5, 124.1], [175.6, 124.9], [175.6, 153.1], [176.5, 154.0], [245.5, 154.0], [246.3, 153.1], [246.3, 124.9], [245.5, 124.1], [176.5, 124.1]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_12', 
       [210.951, 107.85],
       [[176.5, 92.9], [175.6, 93.8], [175.6, 121.9], [176.5, 122.8], [245.5, 122.8], [246.3, 121.9], [246.3, 93.8], [245.5, 92.9], [176.5, 92.9]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_21', 
       [210.951, 76.65],
       [[176.5, 61.7], [175.6, 62.6], [175.6, 90.7], [176.5, 91.6], [245.5, 91.6], [246.3, 90.7], [246.3, 62.6], [245.5, 61.7], [176.5, 61.7]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_20', 
       [139.049, 76.65],
       [[104.5, 61.7], [103.7, 62.6], [103.7, 90.7], [104.5, 91.6], [173.5, 91.6], [174.4, 90.7], [174.4, 62.6], [173.5, 61.7], [104.5, 61.7]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_13', 
       [139.049, 107.85],
       [[104.5, 92.9], [103.7, 93.8], [103.7, 121.9], [104.5, 122.8], [173.5, 122.8], [174.4, 121.9], [174.4, 93.8], [173.5, 92.9], [104.5, 92.9]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_4', 
       [139.049, 139.049],
       [[104.5, 124.1], [103.7, 124.9], [103.7, 153.1], [104.5, 154.0], [173.5, 154.0], [174.4, 153.1], [174.4, 124.9], [173.5, 124.1], [104.5, 124.1]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_0', 
       [139.049, 170.151],
       [[104.5, 155.2], [103.7, 156.1], [103.7, 184.3], [104.5, 185.1], [173.5, 185.1], [174.4, 184.3], [174.4, 156.1], [173.5, 155.2], [104.5, 155.2]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_1', 
       [139.049, 201.35],
       [[104.5, 186.4], [103.7, 187.3], [103.7, 215.4], [104.5, 216.3], [173.5, 216.3], [174.4, 215.4], [174.4, 187.3], [173.5, 186.4], [104.5, 186.4]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_6', 
       [139.049, 232.55],
       [[104.5, 217.6], [103.7, 218.5], [103.7, 246.6], [104.5, 247.5], [173.5, 247.5], [174.4, 246.6], [174.4, 218.5], [173.5, 217.6], [104.5, 217.6]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_15', 
       [139.049, 263.75],
       [[104.5, 248.8], [103.7, 249.7], [103.7, 277.8], [104.5, 278.7], [173.5, 278.7], [174.4, 277.8], [174.4, 249.7], [173.5, 248.8], [104.5, 248.8]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_16', 
       [67.05, 263.75],
       [[32.6, 248.8], [31.7, 249.7], [31.7, 277.8], [32.6, 278.7], [101.5, 278.7], [102.4, 277.8], [102.4, 249.7], [101.5, 248.8], [32.6, 248.8]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_11', 
       [67.05, 232.55],
       [[32.6, 217.6], [31.7, 218.5], [31.7, 246.6], [32.6, 247.5], [101.5, 247.5], [102.4, 246.6], [102.4, 218.5], [101.5, 217.6], [32.6, 217.6]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_9', 
       [67.05, 201.35],
       [[32.6, 186.4], [31.7, 187.3], [31.7, 215.4], [32.6, 216.3], [101.5, 216.3], [102.4, 215.4], [102.4, 187.3], [101.5, 186.4], [32.6, 186.4]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_8', 
       [67.05, 170.151],
       [[32.6, 155.2], [31.7, 156.1], [31.7, 184.3], [32.6, 185.1], [101.5, 185.1], [102.4, 184.3], [102.4, 156.1], [101.5, 155.2], [32.6, 155.2]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_10', 
       [67.05, 139.049],
       [[32.6, 124.1], [31.7, 124.9], [31.7, 153.1], [32.6, 154.0], [101.5, 154.0], [102.4, 153.1], [102.4, 124.9], [101.5, 124.1], [32.6, 124.1]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_14', 
       [67.05, 107.85],
       [[32.6, 92.9], [31.7, 93.8], [31.7, 121.9], [32.6, 122.8], [101.5, 122.8], [102.4, 121.9], [102.4, 93.8], [101.5, 92.9], [32.6, 92.9]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_22', 
       [282.95, 139.049],
       [[248.5, 124.1], [247.6, 124.9], [247.6, 153.1], [248.5, 154.0], [317.4, 154.0], [318.3, 153.1], [318.3, 124.9], [317.4, 124.1], [248.5, 124.1]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_18', 
       [282.95, 170.151],
       [[248.5, 155.2], [247.6, 156.1], [247.6, 184.3], [248.5, 185.1], [317.4, 185.1], [318.3, 184.3], [318.3, 156.1], [317.4, 155.2], [248.5, 155.2]]
    )
    check_def(definitions, 'Leaf_stl_id_1_copy_19', 
       [282.95, 201.35],
       [[248.5, 186.4], [247.6, 187.3], [247.6, 215.4], [248.5, 216.3], [317.4, 216.3], [318.3, 215.4], [318.3, 187.3], [317.4, 186.4], [248.5, 186.4]]
    )
