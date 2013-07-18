import hc2000.validation
import unittest

class ValidateTestCase(unittest.TestCase):
    def validate_test(self, data):
        for validator, data, result in data:
            self.assertEquals(
                bool(hc2000.validation.validate(validator, data)),
                result, 'Test failed: expected %s from validate(%s, %s)'
                    % (result, validator, data))

    def test_is_(self):
        data = [
            (list, [], True),
            (list, "", False),
            (list, {}, False),
            (list, 1, False),

            (basestring, [], False),
            (basestring, "", True),
            (basestring, {}, False),
            (basestring, 1, False),

            (dict, [], False),
            (dict, "", False),
            (dict, {}, True),
            (dict, 1, False),

            (int, [], False),
            (int, "", False),
            (int, {}, False),
            (int, 1, True),
        ]
        self.validate_test(data)

    def test_dict_(self):
        data = [
            ({}, {}, True),
            ({}, [], False),
            ({}, "", False),

            ({ "a": None }, {}, True),
            ({ "a": None }, { "a" : 1 }, True),
            ({ "a": None }, { "b" : 2 }, False),

            ({ "a": None, "b": None }, { "a": 1, "b": 2 }, True),
            ({ "a": None, "b": None }, { "a": 1, "b": 2, "c": 3 }, False),
        ]
        self.validate_test(data)

    def test_path(self):
        data = [
            (hc2000.validation.path, "/etc", True),
            (hc2000.validation.path, "/etc/", True),
            (hc2000.validation.path, "/etc/file", True),
            (hc2000.validation.path, "etc/file", True),
            (hc2000.validation.path, "file", True),

            (hc2000.validation.path, {}, False),
            (hc2000.validation.path, [], False),
            (hc2000.validation.path, 1, False),
        ]
        self.validate_test(data)

    def test_absolute_path(self):
        data = [
            (hc2000.validation.absolute_path, "/etc", True),
            (hc2000.validation.absolute_path, "/etc/", True),
            (hc2000.validation.absolute_path, "/etc/file", True),
            (hc2000.validation.absolute_path, "etc/file", False),
            (hc2000.validation.absolute_path, "file", False),
        ]
        self.validate_test(data)

    def test_file_mode(self):
        data = [
            (hc2000.validation.file_mode, 0755, True),
            (hc2000.validation.file_mode, 0644, True),
            (hc2000.validation.file_mode, 0123, True),
            (hc2000.validation.file_mode, 01000, False),
        ]
        self.validate_test(data)

if __name__ == '__main__':
    unittest.main()
