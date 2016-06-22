import re


class LexerError(Exception):

    def __init__(self, place, msg):
        self.place = place
        self.msg = msg

    def __str__(self):
        s = 'cannot tokenize data'
        line, pos = self.place
        return '%s: %d,%d: "%s"' % (s, line, pos, self.msg)


class Token:

    def __init__(self, type, value, start=None, end=None):
        self.type = type
        self.value = value
        self.start = start
        self.end = end

    def __repr__(self):
        return 'Token(%r, %r)' % (self.type, self.value)

    def __eq__(self, other):
        # FIXME: Case sensitivity is assumed here
        return self.type == other.type and self.value == other.value

    def _pos_str(self):
        if self.start is None or self.end is None:
            return ''
        else:
            sl, sp = self.start
            el, ep = self.end
            return '%d,%d-%d,%d:' % (sl, sp, el, ep)

    def __str__(self):
        s = "%s %s '%s'" % (self._pos_str(), self.type, self.value)
        return s.strip()

    @property
    def name(self):
        return self.value

    def pformat(self):
        return "%s %s '%s'" % (
            self._pos_str().ljust(20), self.type.ljust(14), self.value
        )


def make_tokenizer(specs):
    """[(str, (str, int?))] -> (str -> Iterable(Token))"""

    def compile_spec(spec):
        name, args = spec
        return name, re.compile(*args)

    compiled = [compile_spec(s) for s in specs]

    def match_specs(specs, string, i, position):
        line, pos = position
        for token_type, regexp in specs:
            m = regexp.match(string, i)
            if m is not None:
                value = m.group()
                nls = value.count('\n')
                n_line = line + nls
                if nls == 0:
                    n_pos = pos + len(value)
                else:
                    n_pos = len(value) - value.rfind('\n') - 1
                return Token(
                    token_type, value, (line, pos + 1), (n_line, n_pos)
                )
        else:
            errline = str.splitlines()[line - 1]
            raise LexerError((line, pos + 1), errline)

    def f(string):
        length = len(string)
        line, pos = 1, 0
        i = 0
        while i < length:
            t = match_specs(compiled, string, i, (line, pos))
            yield t
            line, pos = t.end
            i += len(t.value)

    return f
