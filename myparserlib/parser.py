import logging


log = logging.getLogger('myparserlib')
debug = False


class Parser:
    """A wrapper around a parser function that defines some operators for parser
    composition.
    """

    def __init__(self, p):
        """Wraps a parser function p into an object."""
        self.define(p)

    def named(self, name):
        """Specifies the name of the parser for more readable parsing log."""
        self.name = name
        return self

    def define(self, parser):
        """Defines a parser wrapped into this object."""
        lazy_getter = (
            lambda *args, **kwargs:
                getattr(parser, 'run', parser)(*args, **kwargs)
        )
        if debug:
            setattr(self, '_run', lazy_getter)
        else:
            setattr(self, 'run', lazy_getter)
        self.named(getattr(parser, 'name', parser.__doc__))

    def run(self, tokens, state):
        """Sequence(a), State -> (b, State)

        Runs a parser wrapped into this object.
        """
        if debug:
            log.debug('trying %s' % self.name)
        return self._run(tokens, state)

    def _run(self, tokens, s):
        raise NotImplementedError('you must define() a parser')

    def parse(self, tokens):
        """Sequence(a) -> b

        Applies the parser to a sequence of tokens producing a parsing result.

        It provides a way to invoke a parser hiding details related to the
        parser state. Also it makes error messages more readable by specifying
        the position of the rightmost token that has been reached.
        """
        try:
            (tree, _) = self.run(tokens, State())
            return tree
        except NoParseError as e:
            max = e.state.max
            if len(tokens) > max:
                tok = tokens[max]
            else:
                tok = '<EOF>'
            raise NoParseError('%s: %s' % (e.msg, tok), e.state)

    def __add__(self, other):
        """Parser(a, b), Parser(a, c) -> Parser(a, _Tuple(b, c))

        A sequential composition of parsers.

        NOTE: The real type of the parsed value isn't always such as specified.
        Here we use dynamic typing for ignoring the tokens that are of no
        interest to the user. Also we merge parsing results into a single _Tuple
        unless the user explicitely prevents it. See also skip and >>
        combinators.
        """

        def magic(v1, v2):
            vs = [v for v in [v1, v2] if not isinstance(v, _Ignored)]
            if len(vs) == 1:
                return vs[0]
            elif len(vs) == 2:
                if isinstance(vs[0], _Tuple):
                    return _Tuple(v1 + (v2,))
                else:
                    return _Tuple(vs)
            else:
                return _Ignored(())

        @Parser
        def _add(tokens, s):
            (v1, s2) = self.run(tokens, s)
            (v2, s3) = other.run(tokens, s2)
            return magic(v1, v2), s3

        # or in terms of bind and pure:
        # _add = self.bind(lambda x: other.bind(lambda y: pure(magic(x, y))))
        _add.name = '(%s , %s)' % (self.name, other.name)
        return _add

    def __or__(self, other):
        """Parser(a, b), Parser(a, c) -> Parser(a, b or c)

        A choice composition of two parsers.

        NOTE: Here we are not providing the exact type of the result. In a
        statically typed langage something like Either b c could be used. See
        also + combinator.
        """

        @Parser
        def _or(tokens, s):
            try:
                return self.run(tokens, s)
            except NoParseError as e:
                return other.run(tokens, State(s.pos, e.state.max))

        _or.name = '(%s | %s)' % (self.name, other.name)
        return _or

    def __rshift__(self, f):
        """Parser(a, b), (b -> c) -> Parser(a, c)

        Given a function from b to c, transforms a parser of b into a parser of
        c. It is useful for transorming a parser value into another value for
        making it a part of a parse tree or an AST.

        This combinator may be thought of as a functor from b -> c to Parser(a,
        b) -> Parser(a, c).
        """

        @Parser
        def _shift(tokens, s):
            (v, s2) = self.run(tokens, s)
            return f(v), s2

        # or in terms of bind and pure:
        # _shift = self.bind(lambda x: pure(f(x)))
        _shift.name = '(%s)' % (self.name,)
        return _shift

    def bind(self, f):
        """Parser(a, b), (b -> Parser(a, c)) -> Parser(a, c)

        NOTE: A monadic bind function. It is used internally to implement other
        combinators. Functions bind and pure make the Parser a Monad.
        """

        @Parser
        def _bind(tokens, s):
            (v, s2) = self.run(tokens, s)
            return f(v).run(tokens, s2)

        _bind.name = '(%s >>=)' % (self.name,)
        return _bind


class State:
    """A parsing state that is maintained basically for error reporting.

    It consists of the current position pos in the sequence being parsed and
    the position max of the rightmost token that has been consumed while
    parsing.
    """

    def __init__(self, pos=0, max=0):
        self.pos = pos
        self.max = max

    def __str__(self):
        return str((self.pos, self.max))

    def __repr__(self):
        return 'State(%r, %r)' % (self.pos, self.max)


class NoParseError(Exception):

    def __init__(self, msg='', state=None):
        self.msg = msg
        self.state = state

    def __str__(self):
        return self.msg


class _Tuple(tuple):
    pass


class _Ignored(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '_Ignored(%s)' % repr(self.value)


@Parser
def finished(tokens, s):
    """Parser(a, None)

    Throws an exception if any tokens are left in the input unparsed.
    """
    if s.pos >= len(tokens):
        return None, s
    else:
        raise NoParseError('should have reached <EOF>', s)


finished.name = 'finished'


def many(p):
    """Parser(a, b) -> Parser(a, [b])

    Returns a parser that infinitely applies the parser p to the input sequence
    of tokens while it successfully parsers them. The resulting parser returns a
    list of parsed values.
    """

    @Parser
    def _many(tokens, s):
        """Iterative implementation preventing the stack overflow."""
        res = []
        try:
            while True:
                (v, s) = p.run(tokens, s)
                res.append(v)
        except NoParseError as e:
            return res, State(s.pos, e.state.max)

    _many.name = '{ %s }' % p.name
    return _many


def some(pred):
    """(a -> bool) -> Parser(a, a)

    Returns a parser that parses a token if it satisfies a predicate pred.
    """

    @Parser
    def _some(tokens, s):
        if s.pos >= len(tokens):
            raise NoParseError('no tokens left in the stream', s)
        else:
            t = tokens[s.pos]
            if pred(t):
                pos = s.pos + 1
                s2 = State(pos, max(pos, s.max))
                if debug:
                    log.debug('*matched* "%s", new state = %s' % (t, s2))
                return t, s2
            else:
                if debug:
                    log.debug('failed "%s", state = %s' % (t, s))
                raise NoParseError('got unexpected token', s)

    _some.name = '(some)'
    return _some


def a(value):
    """Eq(a) -> Parser(a, a)

    Returns a parser that parses a token that is equal to the value value.
    """
    name = getattr(value, 'name', value)
    return some(lambda t: t == value).named('(a "%s")' % (name,))


def pure(x):
    @Parser
    def _pure(_, s):
        return x, s

    _pure.name = '(pure %r)' % (x,)
    return _pure


def maybe(p):
    """Parser(a, b) -> Parser(a, b or None)

    Returns a parser that retuns None if parsing fails.

    NOTE: In a statically typed language, the type Maybe b could be more
    approprieate.
    """
    return (p | pure(None)).named('[ %s ]' % (p.name,))


def skip(p):
    """Parser(a, b) -> Parser(a, _Ignored(b))

    Returns a parser which results are ignored by the combinator +. It is useful
    for throwing away elements of concrete syntax (e. g. ",", ";").
    """
    return p >> _Ignored


def oneplus(p):
    """Parser(a, b) -> Parser(a, [b])

    Returns a parser that applies the parser p one or more times.
    """
    @Parser
    def _oneplus(tokens, s):
        (v1, s2) = p.run(tokens, s)
        (v2, s3) = many(p).run(tokens, s2)
        return [v1] + v2, s3

    _oneplus.name = '(%s , { %s })' % (p.name, p.name)
    return _oneplus


def with_forward_decls(suspension):
    """(None -> Parser(a, b)) -> Parser(a, b)

    Returns a parser that computes itself lazily as a result of the suspension
    provided. It is needed when some parsers contain forward references to
    parsers defined later and such references are cyclic. See examples for more
    details.
    """

    @Parser
    def f(tokens, s):
        return suspension().run(tokens, s)

    return f


def forward_decl():
    """None -> Parser(?, ?)

    Returns an undefined parser that can be used as a forward declaration. You
    will be able to define() it when all the parsers it depends on are
    available.
    """

    @Parser
    def f(tokens, s):
        raise NotImplementedError('you must define() a forward_decl somewhere')

    return f


if __name__ == '__main__':
    import doctest
    doctest.testmod()
