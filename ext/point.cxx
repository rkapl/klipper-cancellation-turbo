#include "point.h"
#include <structmember.h>

static PyMemberDef Point_members[] = {
    {"x", T_DOUBLE, offsetof(PyPoint, point.x), 0, "x coord"},
    {"y", T_DOUBLE, offsetof(PyPoint, point.y), 0, "y coord"},
    {NULL} 
};

int PyPoint::py_init(PyObject *self, PyObject *args, PyObject *kwds) {
    static const char *names[] = {"x", "y", NULL};
    auto p = reinterpret_cast<PyPoint*>(self);
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "dd", const_cast<char**>(names), &p->point.x, &p->point.y)) {
        return -1;
    }
    return 0;
}

PyTypeObject Point_type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "Point",
    .tp_basicsize = sizeof(PyPoint),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_members = Point_members,
    .tp_init = PyPoint::py_init,
    .tp_new = PyType_GenericNew,
};