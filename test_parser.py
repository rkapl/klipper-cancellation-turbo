import unittest
from preprocess_cancellation_cext import Hull, Point, GCodeParser

def point2tuples(a):
    return [(p.x, p.y) for p in a]

class TestHull(unittest.TestCase):
    def test_points_roundtrip(self):
        h = Hull()
        self.assertEqual(h.points, [])

        point_list = [Point(1, 2), Point(3, 4)]
        h.points = point_list

        # tuples are dumb and not comparable
        self.assertEqual(point2tuples(h.points), point2tuples(point_list))

    def test_point_types(self):
        h = Hull()
        def test_str():
            h.points = 'hello'
        def test_strlist():
            h.points = ['hello']
        self.assertRaises(TypeError, test_str)
        self.assertRaises(TypeError, test_strlist)

class TestParser(unittest.TestCase):
    def test_parser(self):
        h = Hull()
        p = GCodeParser()
        p.hull = h

        p.feed_line('G1 X1 Y2 E1')
        self.assertEqual(point2tuples(h.points), [(1, 2)])

    def test_interests(self):
        p = GCodeParser()
        p.register_interest(';TEST', 77)
        self.assertEqual(77, p.feed_line(';test'))
        


if __name__ == '__main__':
    unittest.main()
