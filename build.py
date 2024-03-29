"""Build script."""
from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError

from setuptools import Extension
from setuptools.command.build_ext import build_ext

extensions = [
    Extension("preprocess_cancellation_cext", sources=["ext/gcode_parser.cxx", "ext/hull.cxx", "ext/point.cxx"]),
]


class BuildFailed(Exception):
    pass


class ExtBuilder(build_ext):
    def run(self):
        try:
            build_ext.run(self)
        except (DistutilsPlatformError, FileNotFoundError):
            pass

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except (CCompilerError, DistutilsExecError, DistutilsPlatformError, ValueError):
            pass


def build(setup_kwargs):
    setup_kwargs.update({
        "ext_modules": extensions,
        "cmdclass": {"build_ext": ExtBuilder},
        "zip_safe": False,
    })