import unittest
import numpy
from preprocess_cancellation_cext import Hull, Point, GCodeParser
import pytest

def point2tuples(a):
    return [(p.x, p.y) for p in a]

def test_points_roundtrip():
    h = Hull()
    assert h.points == []

    point_list = [Point(1, 2), Point(3, 4)]
    h.points = point_list

    # tuples are dumb and not comparable
    assert set(point2tuples(h.points)) == set(point2tuples(point_list))

def test_point_bytes():
    h = Hull()
    point_list = [Point(1, 2), Point(3, 4)]
    h.points = point_list

    a = numpy.frombuffer(h.point_bytes())
    a.shape = (2, 2)
    a = a.copy()
    a.sort(axis=0)
    
    got_list = list(map(tuple, a))

    assert got_list == point2tuples(point_list)

def test_precision():
    h = Hull()
    h.precision = 10
    h.points = [Point(3, 3), Point(6, 6)]

    assert set(point2tuples(h.points)) == set([(0,0), (10, 10)])

def test_point_types():
    h = Hull()

    with pytest.raises(TypeError):
        h.points = 'hello'

    with pytest.raises(TypeError):
        h.points = ['hello']

def test_parser():
    h = Hull()
    p = GCodeParser()
    p.hull = h

    p.feed_line('G1 X1 Y2 E1')
    assert point2tuples(h.points) == [(1, 2)]

def test_interests():
    p = GCodeParser()
    p.register_interest(';TEST', 77)
    assert p.feed_line(';test') == 77
        


if __name__ == '__main__':
    unittest.main()
