#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>

struct Point {
    double x, y;

    Point(double x, double y): x(x), y(y) {}
};


struct PyPoint {
    PyObject_HEAD

    Point point;

    static int py_init(PyObject *self, PyObject *args, PyObject *kwds);
};

extern PyTypeObject Point_type;
