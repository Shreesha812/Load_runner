import re

from models.variable import Variable


class VariableValueParser:
    """
    Parses variable definitions from a single string.

    Braces around value lists are OPTIONAL — both forms are equivalent:

        With braces    : variable1:{a,b,c}, variable2:{x,y}
        Without braces : variable1:a,b,c, variable2:x,y
        Mixed          : variable1:{a,b,c}, variable2:x, variable3:{p,q}
        Single value   : env:staging, version:v2

    The parser tokenises the input by recognising "name:" boundaries,
    so it correctly handles values that contain spaces or commas.
    """

    # Matches "word_chars + optional_spaces + colon" — a variable declaration.
    _VAR_DECL_RE = re.compile(r'(\w+)\s*:')

    def parse(self, value_text: str) -> list[Variable]:
        if not value_text:
            return []

        text = value_text.strip()

        # Collect all (name, colon_end_index) pairs in order
        decls: list[tuple[str, int]] = [
            (m.group(1), m.end())
            for m in self._VAR_DECL_RE.finditer(text)
        ]

        if not decls:
            return []

        variables: list[Variable] = []

        for i, (name, val_start) in enumerate(decls):
            # Slice the raw value segment for this variable.
            # It ends where the NEXT variable's "name:" token begins.
            if i + 1 < len(decls):
                next_name = decls[i + 1][0]
                next_colon_end = decls[i + 1][1]
                seg_end = text.rfind(next_name, val_start, next_colon_end)
                raw = text[val_start:seg_end]
            else:
                raw = text[val_start:]

            # Strip whitespace and trailing separators FIRST,
            # then check for optional surrounding braces.
            raw = raw.strip().rstrip(',').strip()

            if raw.startswith('{') and raw.endswith('}'):
                # Braces present — strip them, they are optional decoration
                raw = raw[1:-1].strip()

            # Split on commas and clean each value
            value_list = [
                v.strip().strip("'\"")
                for v in raw.split(',')
                if v.strip()
            ]

            if value_list:
                variables.append(Variable(name=name, values=value_list))

        return variables
