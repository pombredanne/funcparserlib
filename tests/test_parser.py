import pytest
from myparserlib import parser as p


def test_simple_match():
    a_matcher = p.a('a')

    assert 'a' == a_matcher.parse('a')
    with pytest.raises(p.NoParseError):
        a_matcher.parse('v')


def test_some_match():
    digit_matcher = p.some(lambda item: str.isdigit(item))
    for digit in range(10):
        assert str(digit) == digit_matcher.parse(str(digit))


def test_many_match():
    digit_matcher = p.some(lambda item: str.isdigit(item))
    assert ['1', '2', '3'] == p.many(digit_matcher).parse("123")
