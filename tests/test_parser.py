from myparserlib import parser as p


def test_some():
    digit_matcher = p.some(lambda item: str.isdigit(item))
    for digit in range(10):
        assert str(digit) == digit_matcher.parse(str(digit))


def test_many_match():
    digit_matcher = p.some(lambda item: str.isdigit(item))
    assert ['1', '2', '3'] == p.many(digit_matcher).parse("123")


def test_plus_operator():
    digit_matcher = p.some(lambda item: str.isdigit(item))
    low_letter_matcher = p.some(lambda item: str.islower(item))
    up_letter_matcher = p.some(lambda item: str.isupper(item))

    parser = digit_matcher + low_letter_matcher + up_letter_matcher
    assert ('1', 'a', 'A') == parser.parse("1aA")


def test_or_operator():
    digit_matcher = p.some(lambda item: str.isdigit(item))
    low_letter_matcher = p.some(lambda item: str.islower(item))
    up_letter_matcher = p.some(lambda item: str.isupper(item))

    parser = (digit_matcher | low_letter_matcher | up_letter_matcher)

    assert '1' == parser.parse("1")
    assert 'a' == parser.parse("a")
    assert 'A' == parser.parse("A")
