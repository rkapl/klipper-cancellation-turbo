#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <vector>
#include <unordered_set>
#include "point.h"


struct HullData {
    HullData(): floatPointsValid(false), precision(1) {}
    bool floatPointsValid;
    double precision;
    std::unordered_set<IntPoint> points;
    std::vector<Point> floatPoints;
};

struct Hull {
    PyObject_HEAD
    
    HullData data;

    void addPoint(const Point& p);
    void regenPoints();

    static PyObject *py_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
    static void py_dealloc(PyObject *self);

    static PyObject *py_get_points(Hull *self, void *closure);
    static int py_set_points(Hull *self, PyObject *args, void *closure);

    static PyObject *py_bounding_box(Hull *self, PyObject *args);
    static PyObject *py_point_bytes(Hull *self, PyObject *args);
};

extern PyTypeObject Hull_type;