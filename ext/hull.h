#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <vector>
#include "point.h"


struct HullData {
    std::vector<Point> points;
};

struct Hull {
    PyObject_HEAD
    
    HullData data;

    static PyObject *py_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
    static void py_dealloc(PyObject *self);

    static PyObject *py_get_points(Hull *self, void *closure);
    static int py_set_points(Hull *self, PyObject *args, void *closure);

    static PyObject *py_bounding_box(Hull *self, PyObject *args);
};

extern PyTypeObject Hull_type;