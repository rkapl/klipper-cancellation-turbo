#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string>
#include <stdexcept>
#include "pyref.h"
#include "hull.h"
#include "point.h"

/* Parse G-Code and
 * 1) track points and compute their convex hulls
 * 2) quickly scan the string and tell python code if there is anything interesting there
 */

/* Something like mini-string view */
struct StringSegment {
    StringSegment(): start(nullptr), size(0) {}
    StringSegment(const char* start, size_t size = 1): start(start), size(size) {}

    bool grow() {
        if (start[size] == 0) {
            return false;
        } else {
            size++;
            return true;
        }
    }

    bool cmpi(const char *str) {
        size_t other_size = strlen(str);
        if (size != other_size) {
            return false;
        }
        return strncasecmp(start, str, size);
    }

    std::string string() const{
        return std::string(start, size);
    }

    double atof() const {
        return std::stod(string());
    }

    const char* start;
    size_t size;
};

struct Interest {
    std::string line_start;
    int code;
};

struct GCodeParserData {
    PyRef currentHull;
    std::vector<Interest> interests;
};

struct GCodeParser {
    PyObject_HEAD

    GCodeParserData data;

    static PyObject *py_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
    static void py_dealloc(PyObject *self);

    static int py_set_hull(GCodeParser *self, PyObject *v, void *closure);
    static PyObject *py_get_hull(GCodeParser *self, void *closure);

    static PyObject *py_feed_line(GCodeParser *self, PyObject *args);
    static PyObject *py_register_interest(GCodeParser *self, PyObject *args);
    static PyObject *py_clear_interests(GCodeParser *self, PyObject *args);
};

PyObject *GCodeParser::py_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    if (!PyArg_ParseTuple(args, ""))
        return nullptr;
    PyRef self = PyRef::from_strong(type->tp_alloc(type, 0));
    if (!self)
        return nullptr;
    auto typed = self.cast<GCodeParser>();
    new (&typed->data) GCodeParserData();
    return self.release();
}

void GCodeParser::py_dealloc(PyObject *self) {
    reinterpret_cast<GCodeParser*>(self)->data.~GCodeParserData();
    Py_TYPE(self)->tp_free(self);
}

int GCodeParser::py_set_hull(GCodeParser *self, PyObject *v, void *closure) {
    if (Py_IsNone(v)) {
        self->data.currentHull.reset();
        return 0;
    }
    if (Py_TYPE(v) != &Hull_type) {
        PyErr_Format(PyExc_TypeError,
            "the hull member must be set to a Hull object, not a\"%s\"",
            Py_TYPE(v)->tp_name);
        return -1;
    }

    self->data.currentHull = PyRef::from_borrowed(v);
    return 0;
}

PyObject* GCodeParser::py_get_hull(GCodeParser *self, void *closure) {
    if (self->data.currentHull) {
        return self->data.currentHull.get_and_incref();
    } else {
        Py_RETURN_NONE;
    }
}

PyObject* GCodeParser::py_register_interest(GCodeParser *self, PyObject *args) {
    const char *line_start;
    int code;
    if (!PyArg_ParseTuple(args, "si", &line_start, &code))
        return nullptr;

    Interest i;
    i.code = code;
    i.line_start = line_start;
    self->data.interests.push_back(std::move(i));
    Py_RETURN_NONE;
}

PyObject* GCodeParser::py_clear_interests(GCodeParser *self, PyObject * Py_UNUSED(args)) {
    self->data.interests.clear();
    Py_RETURN_NONE;
}

PyObject *GCodeParser::py_feed_line(GCodeParser *self, PyObject *args)
{
    const char *line_orig;
    if (!PyArg_ParseTuple(args, "s", &line_orig))
        return nullptr;

    const char *line = line_orig;
    /* Skip whitespace */
    while (isspace(*line))
        line++;

    /* Check for interests */
    for (auto& interest: self->data.interests) {
        if (strncasecmp(line, interest.line_start.c_str(), interest.line_start.size()) == 0) {
            return PyLong_FromLong(interest.code);
        }
    }

    if (!self->data.currentHull) {
        Py_RETURN_NONE;
    }

    /* Anything that looks like extrusion move, we remember. Very coarse heuristic, we e.g. assume the slicer
     * is using absolute coordinates. */
    if (tolower(*line) != 'g') {
        Py_RETURN_NONE;
    }

    StringSegment cmd;
    StringSegment argx;
    StringSegment argy;
    StringSegment arge;
    StringSegment unknown;

    /* Parsing helpers */
    auto is_cmd = [](int c) {return !(isspace(c) || c == ';' || c == '\0'); };
    auto consume_command = [&](StringSegment& into) {
        into = StringSegment(line, 0);
        while (is_cmd(*line)) {
            line++;
            into.grow();
        }
    };

    auto skip_whitespace = [&]() {
        while (isspace(*line))
            line++;
    };

    /* Parsing proper */
    consume_command(cmd);
    skip_whitespace();

    while (*line != '\0' && *line != ';') {
        char arg = *line;
        line++;
        switch (toupper(arg)) {
            case 'E':
                consume_command(arge);
                break;
            case 'X':
                consume_command(argx);
                break;
            case 'Y':
                consume_command(argy);
                break;
        }
    }

    /* Evaluate */
    if (argx.size > 0 && argy.size > 0 && arge.size > 0) {
        double x, y, e;
        try {
            x = argx.atof();
            y = argy.atof();
            e = arge.atof();
        } catch (const std::invalid_argument&) {
            // ignore invalid commands
            Py_RETURN_NONE;
        } catch (const std::out_of_range&) {
            // ignore invalid commands
            Py_RETURN_NONE;
        }
        if (e > 0) {
            auto hull = self->data.currentHull.cast<Hull>();
            hull->data.points.emplace_back(x, y);
        }
    }

    Py_RETURN_NONE;
}

static PyMethodDef GCodeParser_methods[] = {
    {"feed_line", (PyCFunction) GCodeParser::py_feed_line, METH_VARARGS, 
        "Feed a line into the parser"
    },
    {"register_interest", (PyCFunction) GCodeParser::py_register_interest, METH_VARARGS, 
        "Register interest in lines starting with a given string. Assign an integer code to the interest that will be returned when matched"
    },
    {"clear_interests", (PyCFunction) GCodeParser::py_clear_interests, METH_NOARGS,
        "Clear all previously registered interests"
    },
    {NULL}  /* Sentinel */
};

static PyGetSetDef GCodeParser_getset[] = {
    {"hull", (getter) GCodeParser::py_get_hull, (setter) GCodeParser::py_set_hull, "current hull to feed points to"},
    {NULL}
};

static PyTypeObject GCodeParser_type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "GCodeParser",
    .tp_basicsize = sizeof(GCodeParser),
    .tp_itemsize = 0,
    .tp_dealloc = GCodeParser::py_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = GCodeParser_methods,
    .tp_getset = GCodeParser_getset,
    .tp_new = GCodeParser::py_new,
};


static struct PyModuleDef mod_gcode_parser = {
     PyModuleDef_HEAD_INIT,
    .m_name = "preprocess_cancellation_cext",
    .m_size = -1,
};

PyMODINIT_FUNC
PyInit_preprocess_cancellation_cext(void)
{
    if (PyType_Ready(&GCodeParser_type) < 0)
        return nullptr;

    if (PyType_Ready(&Hull_type) < 0)
        return nullptr;

    if (PyType_Ready(&Point_type) < 0)
        return nullptr;

    PyRef m = PyRef::from_strong(PyModule_Create(&mod_gcode_parser));
    if (!m)
        return nullptr;

    if (PyModule_AddObjectRef(m.get(), "GCodeParser", reinterpret_cast<PyObject*>(&GCodeParser_type)) < 0)
        return nullptr;

    if (PyModule_AddObjectRef(m.get(), "Hull", reinterpret_cast<PyObject*>(&Hull_type)) < 0)
        return nullptr;

    if (PyModule_AddObjectRef(m.get(), "Point", reinterpret_cast<PyObject*>(&Point_type)) < 0)
        return nullptr;
    
    return m.release();
}