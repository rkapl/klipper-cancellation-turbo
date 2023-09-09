#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <algorithm>

class PyRef {
    public:
        PyRef(): target(nullptr) {}
        PyRef(const PyRef& b): target(nullptr) {
            *this = b;
        }
        PyRef(PyRef&& b): target(nullptr) {
            *this = std::move(b);
        }
        PyRef& operator=(const PyRef& b) {
            reset();
            target = b.target;
            Py_XINCREF(target);
            return *this;
        }
        PyRef& operator=(PyRef&& b) {
            reset();
            target = b.target;
            b.target = nullptr;
            return *this;
        }
        ~PyRef() {
            reset();
        }

        PyObject* operator*() const{
            return target;
        }

        explicit operator bool() const {
            return target;
        }

        bool operator==(PyObject *b) const {
            return target == b;
        }

        void reset() {
            Py_XDECREF(target);
            target = nullptr;
        }

        PyObject *release() {
            auto released = target;
            target = nullptr;
            return released;
        }

        PyObject *get() const {
            return target;
        }

        PyObject *get_and_incref() const {
            Py_XINCREF(target);
            return target;
        }

        template <class T> T* cast() const {
            return reinterpret_cast<T*>(target);
        }

        static PyRef from_strong(PyObject *t) {
            return PyRef(t);
        }

        static PyRef from_borrowed(PyObject *t) {
            Py_XINCREF(t);
            return PyRef(t);
        }

    private:
        PyRef(PyObject *own): target(own) {}
        PyObject *target;
};