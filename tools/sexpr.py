"""Minimal S-expression reader/writer for KiCad files."""


class QStr(str):
    """A string atom that must be written with quotes."""


def parse(text):
    pos = 0
    n = len(text)

    def skip_ws():
        nonlocal pos
        while pos < n and text[pos] in ' \t\r\n':
            pos += 1

    def read():
        nonlocal pos
        skip_ws()
        c = text[pos]
        if c == '(':
            pos += 1
            lst = []
            while True:
                skip_ws()
                if text[pos] == ')':
                    pos += 1
                    return lst
                lst.append(read())
        if c == '"':
            pos += 1
            out = []
            while text[pos] != '"':
                if text[pos] == '\\':
                    pos += 1
                    out.append({'n': '\n', 't': '\t'}.get(text[pos], text[pos]))
                else:
                    out.append(text[pos])
                pos += 1
            pos += 1
            return QStr(''.join(out))
        start = pos
        while pos < n and text[pos] not in ' \t\r\n()':
            pos += 1
        return text[start:pos]

    return read()


def _atom(a):
    if isinstance(a, QStr):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    # Short lists of atoms go on one line.
    if all(not isinstance(x, list) for x in node):
        return '(' + ' '.join(_atom(x) for x in node) + ')'
    pad = '\t' * (indent + 1)
    head = []
    rest = node
    while rest and not isinstance(rest[0], list):
        head.append(_atom(rest[0]))
        rest = rest[1:]
    out = '(' + ' '.join(head)
    for x in rest:
        out += '\n' + pad + dump(x, indent + 1)
    return out + '\n' + '\t' * indent + ')'


def find(node, key):
    """Return first child list whose head is key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
