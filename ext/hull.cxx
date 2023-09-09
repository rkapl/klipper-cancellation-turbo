#include "hull.h"
#include "pyref.h"
#include <limits>

PyObject *Hull::py_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    if (!PyArg_ParseTuple(args, ""))
        return nullptr;
    PyRef self = PyRef::from_strong(type->tp_alloc(type, 0));
    if (!self)
        return nullptr;
    auto typed = self.cast<Hull>();
    new (&typed->data) HullData();
    return self.release();
}

void Hull::py_dealloc(PyObject *self) {
    reinterpret_cast<Hull*>(self)->data.~HullData();
    Py_TYPE(self)->tp_free(self);
}

PyObject* Hull::py_get_points(Hull *self, void *closure) {
    const auto& points = self->data.points;
    PyRef list = PyRef::from_strong(PyList_New(points.size()));
    for (size_t i = 0; i < points.size(); i++) {
        PyRef p(PyRef::from_strong(_PyObject_New(&Point_type)));
        p.cast<PyPoint>()->point = points[i];
        PyList_SetItem(list.get(), i, p.release());
    }
    return list.release();
}

int Hull::py_set_points(Hull *self, PyObject *list, void *closure) {
    auto& points = self->data.points;
    if (!PyList_Check(list)) {
        PyErr_Format(PyExc_TypeError,
                "the points member must be set to a list of Point objects, not a \"%s\"",
                Py_TYPE(list)->tp_name);
        return -1;
    }

    size_t size = PyList_Size(list);
    for (size_t i = 0; i < size; i++) {
        auto p = PyList_GetItem(list, i);
        if (Py_TYPE(p) != &Point_type) {
            PyErr_Format(PyExc_TypeError,
                    "the points member must be set to a list of Point objects, but one of the points is \"%s\"",
                    Py_TYPE(list)->tp_name);
            return -1;
        }
    }

    points.clear();
    points.reserve(size);
    for (size_t i = 0; i < size; i++) {
        auto p = reinterpret_cast<PyPoint*>(PyList_GetItem(list, i));
        points.push_back(p->point);
    }
    return 0;
}

PyObject* Hull::py_bounding_box(Hull *self, PyObject *args) {
    if (self->data.points.empty()) {
        Py_RETURN_NONE;
    }

    double xmin = std::numeric_limits<double>::infinity();
    double ymin = std::numeric_limits<double>::infinity();
    double xmax = -xmin;
    double ymax = -ymin;

    for (const auto& p: self->data.points) {
        xmin = std::min(p.x, xmin);
        ymin = std::min(p.y, ymin);
        xmax = std::max(p.x, xmax);
        ymax = std::max(p.y, ymax);

    }

    return PyTuple_Pack(4, 
        PyFloat_FromDouble(xmin),
        PyFloat_FromDouble(ymin),
        PyFloat_FromDouble(xmax),
        PyFloat_FromDouble(ymax)
    );
}

PyObject* Hull::py_point_bytes(Hull *self, PyObject *args) {

    uint32_t pointsCount = self->data.points.size();
    auto hdrSize = 9;

    PyObject *buf = PyBytes_FromStringAndSize(NULL, 0);
    _PyBytes_Resize(&buf, sizeof(Point) * pointsCount);
    if (!buf)
        return nullptr;
        
    Py_buffer buf_view;
    if (PyObject_GetBuffer(buf, &buf_view, 0) < 0)
        return nullptr;

    memcpy(buf_view.buf, self->data.points.data(), sizeof(Point) * pointsCount);

    PyBuffer_Release(&buf_view);
    return buf;
}


static PyGetSetDef Hull_getset[] = {
    {"points", (getter) Hull::py_get_points, (setter) Hull::py_set_points, "list of collected points for hull calculation"},
    {NULL}
};

static PyMethodDef Hull_methods[] = {
    {"bounding_box", (PyCFunction) Hull::py_bounding_box, METH_NOARGS,
        "Axis-aligned bounding box as (xmin, ymin, xmax, ymax)"
    },
    {"point_bytes", (PyCFunction) Hull::py_point_bytes, METH_NOARGS,
        "Packed points"
    },
    {NULL}
};

 PyTypeObject Hull_type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "Hull",
    .tp_basicsize = sizeof(Hull),
    .tp_itemsize = 0,
    .tp_dealloc = Hull::py_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = Hull_methods,
    .tp_getset = Hull_getset,
    .tp_new = Hull::py_new,
};

