# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.


import collections
import datetime
import decimal
import unittest

from mock import sentinel as sen
from n6sdk.exceptions import (
    FieldValueError,
    FieldValueTooLongError,
)
from n6sdk.data_spec.fields import (
    Field,
    DateTimeField,
    HexDigestField,
    UnicodeField,
    MD5Field,
    SHA1Field,
    UnicodeEnumField,
    UnicodeLimitedField,
    UnicodeRegexField,
    SourceField,
    IPv4Field,
    AnonymizedIPv4Field,
    IPv4NetField,
    CCField,
    URLSubstringField,
    URLField,
    DomainNameSubstringField,
    DomainNameField,
    IntegerField,
    ASNField,
    PortField,
    AddressField)
from n6sdk.datetime_helpers import (
    FixedOffsetTimezone,
)
from n6sdk.tests.test_data_spec import GenericDataSpecTestMixin



#
# Some mix-ins and helpers
#

class FieldTestMixin(GenericDataSpecTestMixin):

    CLASS = None              # must be set in concrete test case classes
    INIT_KWARGS_BASE = None   # can be set in concrete test case classes

    def test__clean_param_value(self):
        for init_kwargs, given, expected in self.cases__clean_param_value():
            assert isinstance(given, basestring)
            init_kwargs = dict(self.INIT_KWARGS_BASE or {}, **init_kwargs)
            f = self.CLASS(**init_kwargs)
            if isinstance(expected, type) and issubclass(
                  expected, BaseException):
                with self.assertRaises(expected):
                    f.clean_param_value(given)
            else:
                cleaned_value = f.clean_param_value(given)
                self.assertEqualIncludingTypes(cleaned_value, expected)

    def test__clean_result_value(self):
        for init_kwargs, given, expected in self.cases__clean_result_value():
            init_kwargs = dict(self.INIT_KWARGS_BASE or {}, **init_kwargs)
            f = self.CLASS(**init_kwargs)
            if isinstance(expected, type) and issubclass(
                  expected, BaseException):
                with self.assertRaises(expected):
                    f.clean_result_value(given)
            else:
                cleaned_value = f.clean_result_value(given)
                self.assertEqualIncludingTypes(cleaned_value, expected)


class case(collections.namedtuple('case', 'init_kwargs, given, expected')):

    def __new__(cls, **kwargs):
        if 'init_kwargs' not in kwargs:
            kwargs['init_kwargs'] = {}
        return super(case, cls).__new__(cls, **kwargs)


#
# Tests of some generic field features
#

class TestInitKwargsAndAttributes(GenericDataSpecTestMixin, unittest.TestCase):

    class MyField(Field):
        foo = sen.foo
        bar = sen.bar

    def _check_std_attrs(self, f,
                         in_result=None,
                         in_params=None,
                         single_param=False,
                         extra_params={},
                         custom_info={}):
        self.assertIs(f.in_result, in_result)
        self.assertIs(f.in_params, in_params)
        self.assertIs(bool(f.single_param), bool(single_param))
        self.assertIsInstance(f.single_param, bool)
        self.assertEqualIncludingTypes(f.extra_params, extra_params)
        self.assertEqualIncludingTypes(f.custom_info, custom_info)

    def test_no_init_kwargs(self):
        f = self.MyField()
        self.assertIs(f.foo, sen.foo)
        self.assertIs(f.bar, sen.bar)
        self.assertEqualIncludingTypes(f._init_kwargs, {})
        self._check_std_attrs(f)

    def test_all_cls_attr_init_kwargs(self):
        f = self.MyField(foo=sen.custom_foo, bar=sen.custom_bar)
        self.assertIs(f.foo, sen.custom_foo)
        self.assertIs(f.bar, sen.custom_bar)
        self.assertEqualIncludingTypes(f._init_kwargs,
                                       dict(foo=sen.custom_foo,
                                            bar=sen.custom_bar))
        self._check_std_attrs(f)

    def test_all_std_attr_init_kwargs(self):
        f = self.MyField(in_result='required',
                         in_params='optional',
                         single_param=True,
                         extra_params=dict(a=sen.a),
                         custom_info=dict(b=sen.b))
        self._check_std_attrs(f,
                              in_result='required',
                              in_params='optional',
                              single_param=True,
                              extra_params=dict(a=sen.a),
                              custom_info=dict(b=sen.b))
        self.assertEqualIncludingTypes(f._init_kwargs,
                                       dict(in_result='required',
                                            in_params='optional',
                                            single_param=True,
                                            extra_params=dict(a=sen.a),
                                            custom_info=dict(b=sen.b)))

    def test_different_attr_init_kwargs(self):
        f = self.MyField(in_result='optional',
                         foo=sen.custom_foo)
        self.assertIs(f.foo, sen.custom_foo)
        self.assertIs(f.bar, sen.bar)
        self._check_std_attrs(f, in_result='optional')
        self.assertEqualIncludingTypes(f._init_kwargs,
                                       dict(in_result='optional',
                                            foo=sen.custom_foo))

    def test_illegal_init_kwargs(self):
        with self.assertRaises(TypeError):
            self.MyField(booo=sen.custom_boo)
        with self.assertRaises(TypeError):
            self.MyField(foo=sen.custom_foo, booo=sen.custom_boo)

    def test_legal_in_params_values(self):
        for value in ('optional', 'required', None):
            f = self.MyField(in_params=value)
            self.assertEqualIncludingTypes(f.in_params, value)

    def test_legal_in_result_values(self):
        for value in ('optional', 'required', None):
            f = self.MyField(in_result=value)
            self.assertEqualIncludingTypes(f.in_result, value)

    def test_illegal_in_params_values(self):
        for value in ('OPTIONAL', False, True, 'blablabla'):
            with self.assertRaises(ValueError):
                self.MyField(in_params=value)

    def test_illegal_in_result_values(self):
        for value in ('OPTIONAL', False, True, 'blablabla'):
            with self.assertRaises(ValueError):
                self.MyField(in_result=value)


class Test_split_raw_param_value(unittest.TestCase):

    def test_ok_for_string(self):
        self.assertEqual(Field()._split_raw_param_value('a'),
                         ['a'])
        self.assertEqual(Field()._split_raw_param_value(u' a ,\nb,c '),
                         [u' a ', u'\nb', u'c '])

    def test_error_for_nonstring(self):
        with self.assertRaises(TypeError):
            self.assertEqual(Field()._split_raw_param_value(None))
        with self.assertRaises(TypeError):
            self.assertEqual(Field()._split_raw_param_value(['a']))


#
# Test of particular field types
#

class TestDateTimeField(FieldTestMixin, unittest.TestCase):

    CLASS = DateTimeField

    def cases__clean_param_value(self):
        yield case(
            given='2014-04-01 01:07',
            expected=datetime.datetime(2014, 4, 1, 1, 7),
        )
        yield case(
            given='2014-04-01 01:07:42.123456+02:00',
            expected=datetime.datetime(2014, 3, 31, 23, 7, 42, 123456),
        )
        yield case(
            given='2014-04-01 01:07:42+02:00',
            expected=datetime.datetime(2014, 3, 31, 23, 7, 42),
        )
        yield case(
            given=u'2015-05-02T24:00',
            expected=datetime.datetime(2015, 5, 3, 0, 0),
        )
        yield case(
            given=u'2015-05-01',
            expected=FieldValueError,
        )
        yield case(
            given='2014-04-01T01:07:42.123456+02:00',
            expected=datetime.datetime(2014, 3, 31, 23, 7, 42, 123456),
        )
        yield case(
            given='2014-04-01T01:07+02:00',
            expected=datetime.datetime(2014, 3, 31, 23, 7, 0),
        )
        yield case(
            given='20140401T010742',
            expected=datetime.datetime(2014, 4, 1, 1, 7, 42),
        )
        yield case(
            given='20140401T010742+02:00',
            expected=datetime.datetime(2014, 3, 31, 23, 7, 42),
        )
        yield case(
            given='20140401010742',
            expected=FieldValueError,
        )
        yield case(
            given='  2014-04-01 01:07:42.123456+02:00  ',
            expected=datetime.datetime(2014, 3, 31, 23, 7, 42, 123456),
        )
        yield case(
            given='2014-04-01      01:07:42.123456+02:00',
            expected=FieldValueError,
        )
        yield case(
            given='',
            expected=FieldValueError,
        )
        yield case(
            given='2014-04-01T01:07:42.123456+02:002014-04-01T01:07:42.123456+02:00',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        dt = datetime.datetime(2014, 3, 31, 23, 7, 42, 123456)
        tz_dt = datetime.datetime(2014, 4, 1, 1, 7, 42, 123456,
                                  tzinfo=FixedOffsetTimezone(120))  # (+02:00)
        yield case(
            given=dt,
            expected=dt,
        )
        yield case(
            given=tz_dt,
            expected=dt,
        )
        yield case(
            given=12345,
            expected=TypeError,
        )


class TestUnicodeField(FieldTestMixin, unittest.TestCase):

    CLASS = UnicodeField

    def cases__clean_param_value(self):
        yield case(
            given=u'ascii',
            expected=u'ascii',
        )
        yield case(
            given='ascii',
            expected=u'ascii',
        )
        yield case(
            given=u'kąŧ¹²³',
            expected=u'kąŧ¹²³',
        )
        yield case(
            given='kąŧ¹²³',
            expected=u'kąŧ¹²³',
        )
        yield case(
            given='123abc   '*100000,
            expected=u'123abc   '*100000,
        )
        yield case(
            given=' ',
            expected=u' ',
        )
        yield case(
            given=''.join(map(chr, range(32, 127))),
            expected=u''.join(map(chr, range(32, 127))),
        )
        yield case(
            given='\x01',
            expected=u'\x01',
        )
        yield case(
            init_kwargs={'encoding': 'utf-8'},
            given=u'fąfara',
            expected=u'fąfara',
        )
        yield case(
            init_kwargs={'encoding': 'utf-8'},
            given='fąfara',
            expected=u'fąfara',
        )
        yield case(
            init_kwargs={'encoding': 'latin-1'},
            given=u'fąfara',
            expected=u'fąfara',
        )
        yield case(
            init_kwargs={'encoding': 'latin-1'},
            given='fąfara',
            expected=u'f\xc4\x85fara',
        )
        yield case(
            init_kwargs={'encoding': 'ascii'},
            given='dd\xdd\xee',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'encoding': 'ascii', 'decode_error_handling': 'replace'},
            given='dd\xdd\xee',
            expected=u'dd\ufffd\ufffd',
        )
        yield case(
            init_kwargs={'encoding': 'utf-8'},
            given='dd\xdd\xee',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'encoding': 'utf-8', 'decode_error_handling': 'ignore'},
            given='dd\xdd\xee',
            expected=u'dd',
        )
        yield case(
            init_kwargs={'encoding': 'utf-8', 'decode_error_handling': 'surrogateescape'},
            given='dd\xdd\xee',                  # non-UTF-8
            expected=u'dd\udcdd\udcee',
        )
        yield case(
            init_kwargs={'encoding': 'utf-8'},
            given='dd\xed\xb3\x9d\xed\xb3\xae',  # already UTF-8
            expected=u'dd\udcdd\udcee',
        )
        yield case(
            init_kwargs={'encoding': 'utf-8'},
            given=u'dd\udcdd\udcee',             # unicode
            expected=u'dd\udcdd\udcee',
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


# TODO:
# * improve test cases (+ remove redundant ones)
# * add __init__ method test
class TestHexDigestField(FieldTestMixin, unittest.TestCase):

    CLASS = HexDigestField
    INIT_KWARGS_BASE = {'num_of_characters': 32, 'hash_algo_descr': 'MD5'}

    def cases__clean_param_value(self):
        yield case(
            given='024a00e7c2ef04ee5b0f767ba73ee397',
            expected=u'024a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given='025a00e7c2ef04ee5b0f767ba73ee397',
            expected=u'025a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given=u'026A00E7C2EF04EE5B0F767BA73EE397',
            expected=u'026a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given=u'023A00E7C2EF04ee5B0F767BA73EE397',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given='023A00E7C2EF04EE5B0F767BA73EE397' + '0',     # too long
            expected=FieldValueError,
        )
        yield case(
            given=u'023A00E7C2EF04EE5B0F767BA73EE39',          # too short
            expected=FieldValueError,
        )
        yield case(
            given='',
            expected=FieldValueError,
        )
        yield case(
            given=u'023A00E7C2EF04EE5B0F767BA73EE397Z',    # illegal chars
            expected=FieldValueError,
        )
        yield case(
            given=32 * ' ',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


# TODO: improve test cases (+ remove redundant ones)
class TestMD5Field(FieldTestMixin, unittest.TestCase):

    CLASS = MD5Field

    def cases__clean_param_value(self):
        yield case(
            given='023a00e7c2ef04ee5b0f767ba73ee397',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given='023A00E7C2EF04ee5B0F767BA73EE397',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given=u'023a00e7c2ef04ee5b0f767ba73ee397',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given=u'023A00E7C2EF04EE5B0F767BA73EE397',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee397',
        )
        yield case(
            given='023a00e7c2ef04ee5b0f767ba73ee397' + '1',   # too long
            expected=FieldValueError,
        )
        yield case(
            given='023a00e7c2ef04ee5b0f767ba73ee39',         # too short
            expected=FieldValueError,
        )
        yield case(
            given=u'',
            expected=FieldValueError,
        )
        yield case(
            given='023a00e7c2ef04zz5b0f767ba73ee397',    # illegal chars
            expected=FieldValueError,
        )
        yield case(
            given=32 * u' ',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestSHA1Field(FieldTestMixin, unittest.TestCase):

    CLASS = SHA1Field

    def cases__clean_param_value(self):
        yield case(
            given='023a00e7c2ef04ee5b0f767ba73ee39701762354',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee39701762354',
        )
        yield case(
            given='023A00E7C2EF04ee5B0F767BA73EE39701762354',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee39701762354',
        )
        yield case(
            given=u'023a00e7c2ef04EE5b0f767ba73ee39701762354',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee39701762354',
        )
        yield case(
            given=u'023A00E7C2EF04EE5B0F767BA73EE39701762354',
            expected=u'023a00e7c2ef04ee5b0f767ba73ee39701762354',
        )
        yield case(
            given=u'023a00e7c2ef04ee5b0f767ba73ee39701762354' + '1',  # too long
            expected=FieldValueError,
        )
        yield case(
            given='023a00e7c2ef04ee5b0f767ba73ee3970176235',         # too short
            expected=FieldValueError,
        )
        yield case(
            given=u'',
            expected=FieldValueError,
        )
        yield case(
            given=u'023a00e7c2ef04zz5b0f767ba73ee39701762354',   # illegal chars
            expected=FieldValueError,
        )
        yield case(
            given=40 * ' ',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


# TODO: add __init__ method test
class TestUnicodeEnumField(FieldTestMixin, unittest.TestCase):

    CLASS = UnicodeEnumField
    INIT_KWARGS_BASE = {'enum_values': ['ABC', u'123', 'en um']}

    def cases__clean_param_value(self):
        yield case(
            given=u'ABC',
            expected=u'ABC',
        )
        yield case(
            given='123',
            expected=u'123',
        )
        yield case(
            given=u'en um',
            expected=u'en um',
        )
        yield case(
            given='NOT in enum',
            expected=FieldValueError,
        )
        yield case(
            given=u'NOT in enum',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'enum_values': ['ąść', '123', 'enum']},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': [u'ąść', '123', 'enum']},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': ['ąść', '123', 'enum']},
            given='ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': [u'ąść', '123', 'enum']},
            given='ąść',
            expected=u'ąść',
        )
        # (note: `enum_values` items being str are always decoded using UTF-8)
        yield case(
            init_kwargs={'enum_values': ['ąść', '123', 'enum'],
                         'encoding': 'iso-8859-2'},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': [u'ąść', '123', 'enum'],
                         'encoding': 'iso-8859-2'},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': ['ąść', '123', 'enum'],
                         'encoding': 'iso-8859-2'},
            given='ąść',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'enum_values': [u'ąść', '123', 'enum'],
                         'encoding': 'iso-8859-2'},
            given='ąść',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'enum_values': ['ąść', '123', 'enum'],
                         'encoding': 'iso-8859-2'},
            given=u'ąść'.encode('iso-8859-2'),
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': [u'ąść', '123', 'enum'],
                         'encoding': 'iso-8859-2'},
            given=u'ąść'.encode('iso-8859-2'),
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'enum_values': [u'\x0c\r\x0e', '123', 'enum']},
            given=u'\x0c\r\x0e',
            expected=u'\x0c\r\x0e',
        )
        yield case(
            init_kwargs={'enum_values': [u'\x0c\r\x0e', '123', 'enum']},
            given='\x0c\r\x0e',
            expected=u'\x0c\r\x0e',
        )
        yield case(
            init_kwargs={'enum_values': [u'\udcdd', '123', 'enum']},
            given=u'\udcdd',
            expected=u'\udcdd',
        )
        yield case(
            init_kwargs={'enum_values': [u'\udcdd', '123', 'enum']},
            given='\xdd',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'enum_values': [u'\udcdd', '123', 'enum'],
                         'decode_error_handling': 'surrogateescape'},
            given='\xdd',
            expected=u'\udcdd',
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            init_kwargs={'enum_values': ['123']},
            given=123,
            expected=TypeError,
        )
        yield case(
            init_kwargs={'enum_values': ['123']},
            given=None,
            expected=TypeError,
        )


# TODO: add __init__ method test
class TestUnicodeLimitedField(FieldTestMixin, unittest.TestCase):

    CLASS = UnicodeLimitedField

    def cases__clean_param_value(self):
        yield case(
            init_kwargs={'max_length': 3},
            given=u'abc',
            expected=u'abc',
        )
        yield case(
            init_kwargs={'max_length': 3},
            given='abc',
            expected=u'abc',
        )
        yield case(
            init_kwargs={'max_length': 2},
            given=u'abc',
            expected=FieldValueTooLongError,
        )
        yield case(
            init_kwargs={'max_length': 2},
            given='abc',
            expected=FieldValueTooLongError,
        )
        yield case(
            init_kwargs={'max_length': 6},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'max_length': 6},
            given='ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'max_length': 5, 'checking_bytes_length': True},
            given=u'ąść',
            expected=FieldValueTooLongError,
        )
        yield case(
            init_kwargs={'max_length': 5, 'checking_bytes_length': True},
            given='ąść',
            expected=FieldValueTooLongError,
        )
        yield case(
            init_kwargs={'max_length': 3, 'checking_bytes_length': False},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'max_length': 3, 'checking_bytes_length': False},
            given='ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'max_length': 3, 'encoding': 'iso-8859-2'},
            given=u'ąść',
            expected=u'ąść',
        )
        yield case(
            init_kwargs={'max_length': 4},
            given=u'too long',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'max_length': 3},
            given=''.join(map(chr, range(12, 15))),  # \x0c\r\x0e
            expected=u'\x0c\r\x0e',
        )
        s = '\xdd \xee'
        u = u'\udcdd \udcee'
        yield case(
            init_kwargs={'max_length': 7},
            given=s,
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'max_length': 7,
                         'decode_error_handling': 'surrogateescape'},
            given=s,
            expected=u,
        )
        yield case(
            init_kwargs={'max_length': 7},
            given=u,
            expected=u,
        )
        yield case(
            init_kwargs={'max_length': 6,
                         'decode_error_handling': 'surrogateescape',
                         'checking_bytes_length': True},
            given=s,
            expected=FieldValueTooLongError,
        )
        yield case(
            init_kwargs={'max_length': 6,
                         'checking_bytes_length': True},
            given=u,
            expected=FieldValueTooLongError,
        )
        yield case(
            init_kwargs={'max_length': 6,
                         'decode_error_handling': 'surrogateescape',
                         'checking_bytes_length': False},
            given=s,
            expected=u,
        )
        yield case(
            init_kwargs={'max_length': 6,
                         'checking_bytes_length': False},
            given=u,
            expected=u,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            init_kwargs={'max_length': 6},
            given=123,
            expected=TypeError,
        )
        yield case(
            init_kwargs={'max_length': 6},
            given=None,
            expected=TypeError,
        )


# TODO: add __init__ method test
class TestUnicodeRegexField(FieldTestMixin, unittest.TestCase):

    CLASS = UnicodeRegexField

    def cases__clean_param_value(self):
        yield case(
            init_kwargs={'regex': r'axc'},
            given='abbbc',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'regex': r'ab{3}c',
                         'error_msg_template': u'"{}" is not a valid value'},
            given='abbbc',
            expected=u'abbbc',
        )
        yield case(
            init_kwargs={'regex': r'axc',
                         'error_msg_template': u'"{}" is not a valid value'},
            given=u'abbbc',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'regex': r'ab{3}c'},
            given=u'abbbc',
            expected=u'abbbc',
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            init_kwargs={'regex': r'123'},
            given=123,
            expected=TypeError,
        )
        yield case(
            init_kwargs={'regex': r'123'},
            given=None,
            expected=TypeError,
        )


class TestSourceField(FieldTestMixin, unittest.TestCase):

    CLASS = SourceField

    def cases__clean_param_value(self):
        yield case(
            given=u'foo-foo.bar',
            expected=u'foo-foo.bar',
        )
        yield case(
            given='-spam.ha--m--',
            expected=u'-spam.ha--m--',
        )
        yield case(
            given=u'x.' + 30 * 'y',
            expected=u'x.' + 30 * 'y',
        )
        yield case(
            given='x.y',
            expected=u'x.y',
        )
        yield case(
            given=u'foo-foo',          # no dot
            expected=FieldValueError,
        )
        yield case(
            given='foo-foo.bar.spam',  # more than one dot
            expected=FieldValueError,
        )
        yield case(
            given=u'Foo-FOO.bar',      # illegal characters (here: uppercase letters)
            expected=FieldValueError,
        )
        yield case(
            given='foo_foo.bar',       # illegal character (here: underscore)
            expected=FieldValueError,
        )
        yield case(
            given=u'foo-foo.',         # no characters after the dot
            expected=FieldValueError,
        )
        yield case(
            given='.bar',              # no characters before the dot
            expected=FieldValueError,
        )
        yield case(
            given=u'.',                # lone dot
            expected=FieldValueError,
        )
        yield case(
            given='x.' + 31 * 'y',     # too long
            expected=FieldValueTooLongError,
        )
        yield case(
            given=u'',                 # empty
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestIPv4Field(FieldTestMixin, unittest.TestCase):

    CLASS = IPv4Field

    def cases__clean_param_value(self):
        yield case(
            given='123.45.67.8',
            expected=u'123.45.67.8',
        )
        yield case(
            given=u'0.0.0.0',
            expected=u'0.0.0.0',
        )
        yield case(
            given='255.255.255.255',
            expected=u'255.255.255.255',
        )
        yield case(
            given=u' 255.255.255.255',
            expected=FieldValueError
        )
        yield case(
            given='255.255.255.255 ',
            expected=FieldValueError
        )
        yield case(
            given=u'256.256.256.256',
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.256',
            expected=FieldValueError
        )
        yield case(
            given=u'23.456.111.123',
            expected=FieldValueError
        )
        yield case(
            given='123.123.111.12.',
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.ff',
            expected=FieldValueError
        )
        yield case(
            given='1.44.22.44',
            expected=u'1.44.22.44',
        )
        yield case(
            given=u'1.1.22.44',
            expected=u'1.1.22.44',
        )
        yield case(
            given='2.34.22.44',
            expected=u'2.34.22.44',
        )
        yield case(
            given=u'2.3U.22.44',
            expected=FieldValueError,
        )
        yield case(
            given='1234',
            expected=FieldValueError,
        )
        yield case(
            given=u'192.168.56.1/20',
            expected=FieldValueError,
        )
        yield case(
            given='192.168.56. 1',
            expected=FieldValueError,
        )
        yield case(
            given=u'192 .168.56.1',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestAnonymizedIPv4Field(FieldTestMixin, unittest.TestCase):

    CLASS = AnonymizedIPv4Field

    def cases__clean_param_value(self):
        yield case(
            given=u'x.234.5.67',
            expected=u'x.234.5.67',
        )
        yield case(
            given='x.234.5.67',
            expected=u'x.234.5.67',
        )
        yield case(
            given=u'X.234.5.67',
            expected=u'x.234.5.67',
        )
        yield case(
            given='X.234.5.67',
            expected=u'x.234.5.67',
        )
        yield case(
            given=u'x.x.0.1',
            expected=u'x.x.0.1',
        )
        yield case(
            given='x.0.x.1',
            expected=u'x.0.x.1',
        )
        yield case(
            given=u'X.0.X.1',
            expected=u'x.0.x.1',
        )
        yield case(
            given='X.0.X.1',
            expected=u'x.0.x.1',
        )
        yield case(
            given=u'x.x.255.x',
            expected=u'x.x.255.x',
        )
        yield case(
            given='x.X.x.255',
            expected=u'x.x.x.255',
        )
        yield case(
            given=u'x.x.x.256',
            expected=FieldValueError,
        )
        yield case(
            given='x.x.x.-1',
            expected=FieldValueError,
        )
        yield case(
            given=u' x.x.x.255',
            expected=FieldValueError,
        )
        yield case(
            given='x.x.x.255 ',
            expected=FieldValueError,
        )
        yield case(
            given=u'255.255.255.x',
            expected=FieldValueError
        )
        yield case(
            given='1.2.x.x',
            expected=FieldValueError
        )
        yield case(
            given=u'32.123.234.56',  # not anonymized
            expected=FieldValueError
        )
        yield case(
            given='x.456.111.123',
            expected=FieldValueError
        )
        yield case(
            given=u'x.123.x.12.',    # extra dot
            expected=FieldValueError
        )
        yield case(
            given='x.x.x.ff',
            expected=FieldValueError
        )
        yield case(
            given=u'x.x.x.x',
            expected=u'x.x.x.x'
        )
        yield case(
            given='X.X.X.X',
            expected=u'x.x.x.x'
        )
        yield case(
            given=u'x.X.x.X',
            expected=u'x.x.x.x'
        )
        yield case(
            given='X.X.x.x',
            expected=u'x.x.x.x'
        )
        yield case(
            given=u'x.x.x.x.x',
            expected=FieldValueError
        )
        yield case(
            given='x.44.22.33.55',
            expected=FieldValueError,
        )
        yield case(
            given=u'1.x.12.33',
            expected=FieldValueError,
        )
        yield case(
            given='x.12.33',
            expected=FieldValueError,
        )
        yield case(
            given=u'\u0120.66.22.44',
            expected=FieldValueError,
        )
        yield case(
            given='x.123.45.1/20',
            expected=FieldValueError,
        )
        yield case(
            given=u'169090601',
            expected=FieldValueError,
        )
        yield case(
            given='x.45.67.8.',
            expected=FieldValueError,
        )
        yield case(
            given=u'y.45.67.8',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=169090601,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestIPv4NetField(FieldTestMixin, unittest.TestCase):

    CLASS = IPv4NetField

    def cases__clean_param_value(self):
        yield case(
            given=u'1.23.4.56/4',
            expected=(u'1.23.4.56', 4),
        )
        yield case(
            given='1.23.4.56/4',
            expected=(u'1.23.4.56', 4),
        )
        yield case(
            given=u'0.0.0.0/0',
            expected=(u'0.0.0.0', 0),
        )
        yield case(
            given='0.0.0.0/0',
            expected=(u'0.0.0.0', 0),
        )
        yield case(
            given=u'255.255.255.255/32',
            expected=(u'255.255.255.255', 32),
        )
        yield case(
            given='255.255.255.255/32',
            expected=(u'255.255.255.255', 32),
        )
        yield case(
            given=u'256.256.256.256/32',  # bad address
            expected=FieldValueError,
        )
        yield case(
            given='10.46.111.123/32',
            expected=(u'10.46.111.123', 32)
        )
        yield case(
            given=u'123.123.111.12/33',   # bad network
            expected=FieldValueError
        )
        yield case(
            given='255.255.255.255/33',   # bad network
            expected=FieldValueError,
        )
        yield case(
            given=u'10.166.77.88.99/4',   # bad address
            expected=FieldValueError,
        )
        yield case(
            given='10.166.88/4',          # bad address
            expected=FieldValueError,
        )
        yield case(
            given=u'1.2.3.4',             # not cidr
            expected=FieldValueError,
        )
        yield case(
            given=u'1.2.3.25 /12',
            expected=FieldValueError
        )
        yield case(
            given=u'1.2.3.25/ 12',
            expected=FieldValueError
        )
        yield case(
            given=u'1.2.3.25./12',
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.0xff/22',
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.07/22',  # leading 0 in cidr ip not allowed
            expected=FieldValueError
        )

    def cases__clean_result_value(self):
        # string given
        yield case(
            given=u'1.23.4.56/4',
            expected=u'1.23.4.56/4',
        )
        yield case(
            given='1.23.4.56/4',
            expected=u'1.23.4.56/4',
        )
        yield case(
            given=u'0.0.0.0/0',
            expected=u'0.0.0.0/0',
        )
        yield case(
            given='0.0.0.0/0',
            expected=u'0.0.0.0/0',
        )
        yield case(
            given=u'255.255.255.255/32',
            expected=u'255.255.255.255/32',
        )
        yield case(
            given='255.255.255.255/32',
            expected=u'255.255.255.255/32',
        )
        yield case(
            given=u'256.256.256.256/32',  # bad address
            expected=FieldValueError,
        )
        yield case(
            given='10.46.111.123/32',
            expected=u'10.46.111.123/32'
        )
        yield case(
            given=u'123.123.111.12/33',   # bad network
            expected=FieldValueError
        )
        yield case(
            given='255.255.255.255/33',   # bad network
            expected=FieldValueError,
        )
        yield case(
            given=u'10.166.77.88.99/4',   # bad address
            expected=FieldValueError,
        )
        yield case(
            given='10.166.88/4',          # bad address
            expected=FieldValueError,
        )
        yield case(
            given=u'1.2.3.4',             # no network
            expected=FieldValueError,
        )
        yield case(
            given='1.2.3.4/',             # no network
            expected=FieldValueError,
        )
        yield case(
            given=u'1.2.3.25 /12',
            expected=FieldValueError
        )
        yield case(
            given=u'1.2.3.25/ 12',
            expected=FieldValueError
        )
        yield case(
            given=u'1.2.3.25./12',
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.0xff/22',
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.07/22',  # leading 0 in ip not allowed
            expected=FieldValueError
        )
        yield case(
            given='1.2.3.7/022',  # leading 0 in network not allowed
            expected=FieldValueError
        )
        yield case(
            given='123/22',
            expected=FieldValueError
        )
        yield case(
            given='',
            expected=FieldValueError
        )
        # non-string iterable given
        yield case(
            given=(u'1.23.4.56', 4),
            expected=u'1.23.4.56/4',
        )
        yield case(
            given=['1.23.4.56', 4],
            expected=u'1.23.4.56/4',
        )
        yield case(
            given=(u'0.0.0.0', u'0'),
            expected=u'0.0.0.0/0',
        )
        yield case(
            given=('0.0.0.0', '0'),
            expected=u'0.0.0.0/0',
        )
        yield case(
            given=[u'255.255.255.255', '32'],
            expected=u'255.255.255.255/32',
        )
        yield case(
            given=('255.255.255.255', 32),
            expected=u'255.255.255.255/32',
        )
        yield case(
            given=(u'256.256.256.256', 32),    # bad address
            expected=FieldValueError,
        )
        yield case(
            given=('10.46.111.123', u'32'),
            expected=u'10.46.111.123/32'
        )
        yield case(
            given=(u'123.123.111.12', u'33'),  # bad network
            expected=FieldValueError
        )
        yield case(
            given=('255.255.255.255', 33),     # bad network
            expected=FieldValueError,
        )
        yield case(
            given=(u'10.166.77.88.99', 4),     # bad address
            expected=FieldValueError,
        )
        yield case(
            given=('10.166.88', 4),            # bad address
            expected=FieldValueError,
        )
        yield case(
            given=(u'1.2.3.25 ', 12),
            expected=FieldValueError
        )
        yield case(
            given=(u' 1.2.3.25', 12),
            expected=FieldValueError
        )
        yield case(
            given=(u'1.2.3.25.', 12),
            expected=FieldValueError
        )
        yield case(
            given=('1.2.3.0xff', 22),
            expected=FieldValueError
        )
        yield case(
            given=('1.2.3.07', 22),  # leading 0 in cidr ip not allowed
            expected=FieldValueError
        )
        yield case(
            given=('123', 22),
            expected=FieldValueError
        )
        yield case(
            given=('', 22),
            expected=FieldValueError
        )
        yield case(
            given=('1.2.3.4', ''),
            expected=FieldValueError
        )
        yield case(
            given=(123, 22),
            expected=FieldValueError
        )
        yield case(
            given=123,
            expected=FieldValueError,
        )
        yield case(
            given=None,
            expected=FieldValueError,
        )


class TestCCField(FieldTestMixin, unittest.TestCase):

    CLASS = CCField

    def cases__clean_param_value(self):
        yield case(
            given='PL',
            expected=u'PL',
        )
        yield case(
            given=u'PL',
            expected=u'PL',
        )
        yield case(
            given='pl',
            expected=u'PL',
        )
        yield case(
            given=u'pL',
            expected=u'PL',
        )
        yield case(
            given='PRL',
            expected=FieldValueError,
        )
        yield case(
            given=u'PRL',
            expected=FieldValueError,
        )
        yield case(
            given='P1',
            expected=u'P1',  # ok
        )
        yield case(
            given='1P',
            expected=FieldValueError,
        )
        yield case(
            given='PL0',
            expected=FieldValueError,
        )
        yield case(
            given='1.23.4.56/4',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestURLField(FieldTestMixin, unittest.TestCase):

    CLASS = URLField

    def cases__clean_param_value(self):
        yield case(
            given='http://www.test.pl',
            expected=u'http://www.test.pl',
        )
        yield case(
            given=u'http://www.test.pl/cgi-bin/foo.pl',
            expected=u'http://www.test.pl/cgi-bin/foo.pl',
        )
        yield case(
            given='http://www.test.pl/cgi/bin/foo.pl?debug=1&id=123',
            expected=u'http://www.test.pl/cgi/bin/foo.pl?debug=1&id=123',
        )
        yield case(
            given=('http://www.TEST.pl/cgi-bin/bar.pl?mode=browse&amp;'
                   'debug=%20123&amp;id=k-%5D'),
            expected=(u'http://www.TEST.pl/cgi-bin/bar.pl?mode=browse&amp;'
                      u'debug=%20123&amp;id=k-%5D'),
        )
        yield case(
            given='http://tęst.pl\xdd',
            expected=u'http://t\u0119st.pl\udcdd',
        )
        yield case(
            given=u'http://tęst.pl\udcdd',
            expected=u'http://t\u0119st.pl\udcdd',
        )
        yield case(
            given='http://test.pl',
            expected=u'http://test.pl',
        )
        yield case(
            given=('http://example.net/search.php?q=разные+авторы\r\n'),
            expected=(u'http://example.net/search.php?q=разные+авторы\r\n'),
        )
        yield case(
            given=(u'http://example.net/search.php?q=разные+авторы\r\n'),
            expected=(u'http://example.net/search.php?q=разные+авторы\r\n'),
        )
        yield case(
            given=u'http://example.net/search.php?\t',
            expected=u'http://example.net/search.php?\t',
        )
        yield case(
            given='',
            expected=u'',
        )
        yield case(
            given=u'',
            expected=u'',
        )
        yield case(
            given='https://' + 'x.pl'*1000,  # too long
            expected=FieldValueTooLongError,
        )
        yield case(
            given='https://' + 'x'*2040,     # len 2048
            expected=u'https://' + 'x'*2040,
        )
        yield case(
            given='https://x' + 'x'*2040,    # too long (2049)
            expected=FieldValueTooLongError,
        )
        yield case(
            given=u'https://' + 'x'*2040,    # len 2048
            expected=u'https://' + 'x'*2040,
        )
        yield case(
            given=u'https://x' + 'x'*2040,   # too long (2049)
            expected=FieldValueTooLongError,
        )
        yield case(
            given='https://dd\xdd\xee',                  # non-UTF-8
            expected=u'https://dd\udcdd\udcee',
        )
        yield case(
            given='https://dd\xed\xb3\x9d\xed\xb3\xae',  # already UTF-8
            expected=u'https://dd\udcdd\udcee',
        )
        yield case(
            given=u'https://dd\udcdd\udcee',             # unicode
            expected=u'https://dd\udcdd\udcee',
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestURLSubstringField(TestURLField):

    CLASS = URLSubstringField


class TestDomainNameSubstringField(FieldTestMixin, unittest.TestCase):

    CLASS = DomainNameSubstringField

    def cases__clean_param_value(self):
        yield case(
            given='test.pl',
            expected=u'test.pl',
        )
        yield case(
            given=u'test.pl',
            expected=u'test.pl',
        )
        yield case(
            given='-te--st-.p-l',
            expected=u'-te--st-.p-l',
        )
        yield case(
            given=u'-te--st-.p-l',
            expected=u'-te--st-.p-l',
        )
        yield case(
            given='abcx' + '.m' * 126,    # too long (>255)
            expected=FieldValueTooLongError,
        )
        yield case(
            given=u'abcx' + u'.m' * 126,  # too long (>255)
            expected=FieldValueTooLongError,
        )
        yield case(
            given='yyy' + '.x' * 126,     # ok, len 255
            expected=u'yyy' + '.x' * 126,
        )
        yield case(
            given=u'yyy' + u'.x' * 126,   # ok, len 255
            expected=u'yyy' + '.x' * 126,
        )
        yield case(
            given='abc.' + 'm' * 64,      # single label too long
            expected=FieldValueError,
        )
        yield case(
            given=u'abc.' + u'm' * 64,    # single label too long
            expected=FieldValueError,
        )
        yield case(
            given='abc.' + 'm' * 63,      # ok, single label len 63
            expected=u'abc.' + 'm' * 63,
        )
        yield case(
            given=u'abc.' + 'm' * 63,     # ok, single label len 63
            expected=u'abc.' + u'm' * 63,
        )
        yield case(
            given='test.fałszywa.domena.example.com',
            expected=u'test.xn--faszywa-ojb.domena.example.com',
        )
        yield case(
            given=u'Test.fałszyWa.DOmena.example.com',
            expected=u'test.xn--faszywa-ojb.domena.example.com',
        )
        yield case(
            given='mMm.WWW.pl',
            expected=u'mmm.www.pl',
        )
        yield case(
            given=u'qQq. pl. . .',
            expected=u'qqq. pl. . .',
        )
        yield case(
            given='life_does_not_work_according_to.rfc',
            expected=u'life_does_not_work_according_to.rfc',
        )
        yield case(
            given=u'life_does_not_work_according_to.rfc',
            expected=u'life_does_not_work_according_to.rfc',
        )
        yield case(
            given='',
            expected=u'',
        )
        yield case(
            given=u'',
            expected=u'',
        )
        yield case(
            given='!@#$%^&*()+=[]',
            expected=u'!@#$%^&*()+=[]',
        )
        yield case(
            given=u'!@#$%^&*()+=[]',
            expected=u'!@#$%^&*()+=[]',
        )
        yield case(
            given='!@#$%^&*()+=[]ąć.pl',
            expected=u'xn--!@#$%^&*()+=[]-owb6a.pl',
        )
        yield case(
            given=u'!@#$%^&*()+=[]ąć.pl',
            expected=u'xn--!@#$%^&*()+=[]-owb6a.pl',
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


class TestDomainNameField(FieldTestMixin, unittest.TestCase):

    CLASS = DomainNameField

    def cases__clean_param_value(self):
        yield case(
            given='test.pl',
            expected=u'test.pl',
        )
        yield case(
            given=u'test.pl',
            expected=u'test.pl',
        )
        yield case(
            given='-te--st-.p-l',
            expected=u'-te--st-.p-l',
        )
        yield case(
            given=u'-te--st-.p-l',
            expected=u'-te--st-.p-l',
        )
        yield case(
            given='abcx' + '.m' * 126,    # too long (>255)
            expected=FieldValueTooLongError,
        )
        yield case(
            given=u'abcx' + u'.m' * 126,  # too long (>255)
            expected=FieldValueTooLongError,
        )
        yield case(
            given='yyy' + '.x' * 126,     # ok, len 255
            expected=u'yyy' + '.x' * 126,
        )
        yield case(
            given=u'yyy' + u'.x' * 126,   # ok, len 255
            expected=u'yyy' + '.x' * 126,
        )
        yield case(
            given='abc.' + 'm' * 63,      # ok, single label len 63
            expected=u'abc.' + 'm' * 63,
        )
        yield case(
            given=u'abc.' + 'm' * 63,     # ok, single label len 63
            expected=u'abc.' + u'm' * 63,
        )
        yield case(
            given='abc.' + 'm' * 64,      # single label too long
            expected=FieldValueError,
        )
        yield case(
            given=u'abc.' + u'm' * 64,    # single label too long
            expected=FieldValueError,
        )
        yield case(
            given='test.fałszywa.domena.example.com',
            expected=u'test.xn--faszywa-ojb.domena.example.com',
        )
        yield case(
            given=u'Test.fałszyWa.DOmena.example.com',
            expected=u'test.xn--faszywa-ojb.domena.example.com',
        )
        yield case(
            given='mMm.WWW.pl',
            expected=u'mmm.www.pl',
        )
        yield case(
            given=u'qQq. pl. . .',
            expected=FieldValueError,
        )
        yield case(
            given='life_does_not_work_according_to.rfc',
            expected=u'life_does_not_work_according_to.rfc',
        )
        yield case(
            given=u'life_does_not_work_according_to.rfc',
            expected=u'life_does_not_work_according_to.rfc',
        )
        yield case(
            given='',
            expected=FieldValueError,
        )
        yield case(
            given=u'',
            expected=FieldValueError,
        )
        yield case(
            given='!@#$%^&*()+=[]',
            expected=FieldValueError,
        )
        yield case(
            given=u'!@#$%^&*()+=[]ąć',
            expected=FieldValueError,
        )
        yield case(
            given='!@#$%^&*()+=[]ąć.pl',
            expected=FieldValueError,
        )
        yield case(
            given=u'!@#$%^&*()+=[]ąć.pl',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=123,
            expected=TypeError,
        )
        yield case(
            given=None,
            expected=TypeError,
        )


# TODO: improve test cases
# (especially add some without min/max limits)
class TestIntegerField(FieldTestMixin, unittest.TestCase):

    CLASS = IntegerField

    def cases__clean_param_value(self):
        init_kwargs = {
            'min_value': 10,
            'max_value': 123,
        }
        yield case(
            init_kwargs=init_kwargs,
            given='11',
            expected=11,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=u'11',
            expected=11,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='10',
            expected=10,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=u'10',
            expected=10,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='9',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='09',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=u'09',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=u'123',
            expected=123,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='124',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given='-2',
            expected=-2,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given=u'-02',
            expected=-2,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given=u'-3',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given='-03',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given='0x1',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'min_value': 10,
                         'max_value': 123000000000000000000000L},
            given='123000000000000000000000',
            expected=123000000000000000000000L,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='123.0',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='0-1',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='',
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given='1.5',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        init_kwargs = {
            'min_value': 10,
            'max_value': 123,
        }
        yield case(
            init_kwargs=init_kwargs,
            given=11,
            expected=11,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=10,
            expected=10,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=9,
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=123,
            expected=123,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=124,
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given=-2,
            expected=-2,
        )
        yield case(
            init_kwargs={'min_value': -2,
                         'max_value': 123,
                         'error_msg_template': u'"{}" is not valid'},
            given=-3,
            expected=FieldValueError,
        )
        yield case(
            init_kwargs={'min_value': 10,
                         'max_value': 123000000000000000000000L},
            given=123000000000000000000000L,
            expected=123000000000000000000000L,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=123L,
            expected=123,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=123.0,
            expected=123,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=decimal.Decimal(123),
            expected=123,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=decimal.Decimal('123.0'),
            expected=123,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=123.1,
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=decimal.Decimal('123.1'),
            expected=FieldValueError,
        )
        yield case(
            given=None,
            expected=FieldValueError,
        )
        yield case(
            init_kwargs=init_kwargs,
            given=None,
            expected=FieldValueError,
        )


class TestASNField(FieldTestMixin, unittest.TestCase):

    CLASS = ASNField

    def cases__clean_param_value(self):
        yield case(
            given='0',
            expected=0,
        )
        yield case(
            given=u'0',
            expected=0,
        )
        yield case(
            given='0.0',
            expected=0,
        )
        yield case(
            given=u'0.0',
            expected=0,
        )
        yield case(
            given='1',
            expected=1,
        )
        yield case(
            given=u'1',
            expected=1,
        )
        yield case(
            given='0.1',
            expected=1,
        )
        yield case(
            given=u'0.1',
            expected=1,
        )
        yield case(
            given='1234',
            expected=1234,
        )
        yield case(
            given=u'0.1234',
            expected=1234,
        )
        yield case(
            given='65535',
            expected=65535,
        )
        yield case(
            given=u'65535',
            expected=65535,
        )
        yield case(
            given='0.65535',
            expected=65535,
        )
        yield case(
            given=u'0.65535',
            expected=65535,
        )
        yield case(
            given='0.65536',
            expected=FieldValueError,
        )
        yield case(
            given=u'0.65536',
            expected=FieldValueError,
        )
        yield case(
            given='42.65536',
            expected=FieldValueError,
        )
        yield case(
            given=u'42.65536',
            expected=FieldValueError,
        )
        yield case(
            given='65536',
            expected=65536,
        )
        yield case(
            given=u'65536',
            expected=65536,
        )
        yield case(
            given='1.0',
            expected=65536,
        )
        yield case(
            given=u'65537',
            expected=65537,
        )
        yield case(
            given=u'1.1',
            expected=65537,
        )
        yield case(
            given='-1',
            expected=FieldValueError,
        )
        yield case(
            given='0.-1',
            expected=FieldValueError,
        )
        yield case(
            given='-1.0',
            expected=FieldValueError,
        )
        yield case(
            given=u'65535.0',
            expected=0xffff << 16,
        )
        yield case(
            given='65535.1',
            expected=(0xffff << 16) + 1,
        )
        yield case(
            given='4294967295',    # max
            expected=4294967295,
        )
        yield case(
            given=u'4294967295',   # max
            expected=4294967295,
        )
        yield case(
            given='65535.65535',   # max
            expected=4294967295,
        )
        yield case(
            given=u'65535.65535',  # max
            expected=4294967295,
        )
        yield case(
            given='4294967296',    # max + 1
            expected=FieldValueError,
        )
        yield case(
            given=u'4294967296',   # max + 1
            expected=FieldValueError,
        )
        yield case(
            given='65536.0',
            expected=FieldValueError,
        )
        yield case(
            given=u'65536.1',
            expected=FieldValueError,
        )
        yield case(
            given='65536.65536',
            expected=FieldValueError,
        )
        yield case(
            given='',
            expected=FieldValueError,
        )
        yield case(
            given=u'asdf',
            expected=FieldValueError,
        )
        yield case(
            given='0.0.0',
            expected=FieldValueError,
        )
        yield case(
            given=u'0x1.0xf',
            expected=FieldValueError,
        )
        yield case(
            given='0xFF',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=-1,
            expected=FieldValueError,
        )
        yield case(
            given=-1L,
            expected=FieldValueError,
        )
        yield case(
            given=0,
            expected=0,
        )
        yield case(
            given=1234L,
            expected=1234,
        )
        yield case(
            given=65535,
            expected=65535,
        )
        yield case(
            given=65536,
            expected=65536,
        )
        yield case(
            given=4294967295,  # max
            expected=4294967295,
        )
        yield case(
            given=4294967296,  # max + 1
            expected=FieldValueError,
        )
        yield case(
            given=0.1,
            expected=FieldValueError,
        )
        yield case(
            given=decimal.Decimal('0.1'),
            expected=FieldValueError,
        )
        yield case(
            given=123.0,
            expected=FieldValueError,
        )
        yield case(
            given=decimal.Decimal(123),
            expected=FieldValueError,
        )
        yield case(
            given=decimal.Decimal('123.0'),
            expected=FieldValueError,
        )
        yield case(
            given=None,
            expected=FieldValueError,
        )


class TestPortField(FieldTestMixin, unittest.TestCase):

    CLASS = PortField

    def cases__clean_param_value(self):
        yield case(
            given='0',       # min
            expected=0,
        )
        yield case(
            given=u'1',
            expected=1,
        )
        yield case(
            given='-1',
            expected=FieldValueError,
        )
        yield case(
            given='65535',   # max
            expected=65535,
        )
        yield case(
            given='65536',   # max + 1
            expected=FieldValueError,
        )
        yield case(
            given='',
            expected=FieldValueError,
        )
        yield case(
            given='1F',
            expected=FieldValueError,
        )
        yield case(
            given='0.1',
            expected=FieldValueError,
        )
        yield case(
            given='1.0',
            expected=FieldValueError,
        )

    def cases__clean_result_value(self):
        for c in self.cases__clean_param_value():
            yield c
        yield case(
            given=-1,
            expected=FieldValueError,
        )
        yield case(
            given=0,
            expected=0,
        )
        yield case(
            given=65535,
            expected=65535,
        )
        yield case(
            given=65536,
            expected=FieldValueError,
        )
        yield case(
            given=123,
            expected=123,
        )
        yield case(
            given=123L,
            expected=123,
        )
        yield case(
            given=123.0,
            expected=123,
        )
        yield case(
            given=decimal.Decimal('123.0'),
            expected=123,
        )
        yield case(
            given=123.1,
            expected=FieldValueError,
        )
        yield case(
            given=decimal.Decimal('123.1'),
            expected=FieldValueError,
        )
        yield case(
            given=None,
            expected=FieldValueError,
        )


# TODO: improve test cases (+ remove redundant ones)
class TestAddressField(FieldTestMixin, unittest.TestCase):

    CLASS = AddressField

    def cases__clean_param_value(self):
        yield case(
            given='not_impl',
            expected=NotImplementedError,
        )

    def cases__clean_result_value(self):
        yield case(
            given=[{'ip': '12.23.45.56', 'cc': 'PL', 'asn': 123}],
            expected=[{u'ip': u'12.23.45.56', u'cc': u'PL', u'asn': 123}],
        )
        yield case(
            given=({'ip': '12.23.45.56', 'cc': 'PL', 'asn': '0.123'},),
            expected=[{u'ip': u'12.23.45.56', u'cc': u'PL', u'asn': 123}],
        )
        yield case(
            given=[{u'ip': u'12.23.45.56', u'cc': u'pL', u'asn': 123L}],
            expected=[{u'ip': u'12.23.45.56', u'cc': u'PL', u'asn': 123}],
        )
        yield case(
            given=(
                {u'ip': u'12.23.45.56', u'cc': u'pL', u'asn': 2 ** 32 - 1},),
            expected=[
                {u'ip': u'12.23.45.56', u'cc': u'PL', u'asn': 2 ** 32 - 1}],
        )
        yield case(
            given=[
                {'ip': u'12.23.45.56', 'cc': 'pl', 'asn': '123'},
                {u'ip': '78.90.122.134', 'asn': u'12345678'},
            ],
            expected=[
                {u'ip': u'12.23.45.56', u'cc': u'PL', u'asn': 123},
                {u'ip': u'78.90.122.134', u'asn': 12345678},
            ],
        )
        yield case(
            # bad ip
            given=[{'ip': u'12.23.45.', 'cc': 'PL', 'asn': 123}],
            expected=FieldValueError,
        )
        yield case(
            # ip must be a str or unicode
            given=[
                {'ip': [u'12.23.45.56', u'12.23.45.45'],
                 'cc': 'PL', 'asn': 123}],
            expected=TypeError,
        )
        yield case(
            # bad cc
            given=[{'ip': u'12.23.45.56', 'cc': 'PRL', 'asn': 123}],
            expected=FieldValueError,
        )
        yield case(
            # bad asn
            given=[{'ip': u'12.23.45.56', 'cc': 'PL', 'asn': 2 ** 32}],
            expected=FieldValueError,
        )
        yield case(
            # illegal key
            given=[
                {'ip': u'12.23.45.56', 'cc': 'PL', 'asn': 123,
                 'fqdn': 'www.example.com'}],
            expected=ValueError,
        )
        yield case(
            # missing 'ip' key
            given=[{'cc': 'pl', 'asn': 123}],
            expected=ValueError,
        )
        yield case(
            # empty sequence
            given=[],
            expected=ValueError,
        )
        yield case(
            init_kwargs={'allow_empty': True},
            given=[],
            expected=[],
        )
        yield case(
            # not a mapping in the sequence
            given=['123'],
            expected=TypeError,
        )
        yield case(
            # not a non-string sequence
            given={'123'},
            expected=TypeError,
        )
        yield case(
            # not a non-string sequence
            given='123',
            expected=TypeError,
        )


# TODO: add dedicated ResultListFieldMixin tests
# TODO: add dedicated DictResultField tests
# (now these classes are tested only indirectly by the AddressField tests)

# class Test(FieldTestMixin, unittest.TestCase):
#
#     CLASS =
#
#     def cases__clean_param_value(self):
#         yield case(
#         )
#
#     def cases__clean_result_value(self):
#         yield case(
#         )
