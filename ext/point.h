#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <functional>

struct Point {
    double x, y;

    Point(double x, double y): x(x), y(y) {}
};

struct IntPoint {
    int x, y;

    IntPoint(int x, int y): x(x), y(y) {}
    
    Point toPoint(double precision) const {
        return Point(x * precision, y * precision);
    }

    static IntPoint fromPoint(double precision, const Point &p) {
        return IntPoint(round(p.x / precision), round(p.y / precision));
    }

    bool operator==(const IntPoint& b) const {
        return this->x == b.x && this->y == b.y;
    }
};

template<>
struct std::hash<IntPoint> {
    std::size_t operator()(const IntPoint& k) const {
        return k.x + ((k.y * 31) << 16);
    }
};


struct PyPoint {
    PyObject_HEAD

    Point point;

    static int py_init(PyObject *self, PyObject *args, PyObject *kwds);
};

extern PyTypeObject Point_type;
