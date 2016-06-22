class ParserRelay:
    parser_registry = dict

    def __getattr__(self, attr_name):
        if attr_name.startswith('p_') and attr_name in self.parser_registry:
            return self.parser_registry[attr_name](self)

        return super().__getattr__(attr_name)

    def __init__(self, **parsers):
        self.parser_registry = self.parser_registry()
        for parser_name, parser_function in parsers.items():
            self.register_parser(parser_name, parser_function)

    def register_parser(self, parser_name, parser_function):
        self.parser_registry[parser_name] = parser_function
