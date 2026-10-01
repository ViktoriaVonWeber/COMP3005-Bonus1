# ============================================================
# ra.py — Relational Algebra Engine
# ============================================================
# Structure:
#   1. Tokenizer     (string -> list of tokens)
#   2. Parser        (tokens -> tree)
#   3. Evaluator     (tree -> result table)
#   4. CLI           (arg parsing, file loading, printing)
# ============================================================


# ============================================================
# PART 1: TOKENS
# ============================================================
# A Token is just a box holding:
#   - kind:  WHAT it is ("IDENT", "NUMBER", "UNION", etc.)
#   - value: the actual text
#   - pos:   WHERE in the input string it started
# ============================================================

class Token:
    def __init__(self, kind, value, pos):
        self.kind = kind
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r}, @{self.pos})"


class TokenError(Exception):
    def __init__(self, message, pos):
        self.message = message
        self.pos = pos
        super().__init__(message)


KEYWORDS = {
    "select":     "SELECT",
    "project":    "PROJECT",
    "rename":     "RENAME",
    "union":      "UNION",
    "intersect":  "INTERSECT",
    "minus":      "MINUS",
    "times":      "TIMES",
    "join":       "JOIN",
    "and":        "AND",
    "or":         "OR",
    "not":        "NOT",
}

TWO_CHAR_OPS = {
    "!=": "NEQ",
    "<=": "LEQ",
    ">=": "GEQ",
}

ONE_CHAR_OPS = {
    "=": "EQ",
    "<": "LT",
    ">": "GT",
    "(": "LPAREN",
    ")": "RPAREN",
    "[": "LBRACK",
    "]": "RBRACK",
    "{": "LBRACE",
    "}": "RBRACE",
    ",": "COMMA",
    ".": "DOT",
}


# ============================================================
# tokenize(source) -> list of Token
# ============================================================
# THE MAIN SCANNER LOOP. Character by character. No regex.
# ============================================================

def tokenize(source):
    tokens = []
    i = 0
    n = len(source)

    while i < n:
        c = source[i]

        # ---- 1. WHITESPACE -----------------------------------
        if c in " \t\r\n":
            i += 1
            continue

        # ---- 2. COMMENTS -------------------------------------
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            i += 2
            while i < n and source[i] != "\n":
                i += 1
            continue

        # ---- 3. NUMBERS --------------------------------------
        if c.isdigit() or (c == "-" and i + 1 < n and source[i + 1].isdigit()):
            start = i
            if c == "-":
                i += 1
            while i < n and source[i].isdigit():
                i += 1
            text = source[start:i]
            tokens.append(Token("NUMBER", text, start))
            continue

        # ---- 4. QUOTED STRINGS -------------------------------
        if c == "'":
            start = i
            i += 1
            chars = []
            closed = False
            while i < n:
                if source[i] == "'":
                    if i + 1 < n and source[i + 1] == "'":
                        chars.append("'")
                        i += 2
                    else:
                        closed = True
                        i += 1
                        break
                else:
                    chars.append(source[i])
                    i += 1
            if not closed:
                raise TokenError("unterminated string literal", start)
            tokens.append(Token("STRING", "".join(chars), start))
            continue

        # ---- 5. IDENTIFIERS ----------------------------------
        if c.isalpha() or c == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            text = source[start:i]
            kind = KEYWORDS.get(text, "IDENT")
            tokens.append(Token(kind, text, start))
            continue

        # ---- 6. TWO-CHARACTER OPERATORS ----------------------
        two = source[i:i + 2]
        if two in TWO_CHAR_OPS:
            tokens.append(Token(TWO_CHAR_OPS[two], two, i))
            i += 2
            continue

        # ---- 7. SINGLE-CHARACTER OPERATORS -------------------
        if c in ONE_CHAR_OPS:
            tokens.append(Token(ONE_CHAR_OPS[c], c, i))
            i += 1
            continue

        # ---- 8. LEXICAL ERROR --------------------------------
        raise TokenError(f"unexpected character {c!r}", i)

    tokens.append(Token("EOF", "", n))
    return tokens


# ============================================================
# PART 2: THE TREE NODES
# ============================================================

class Node:
    def tree_str(self, indent=0):
        raise NotImplementedError


class RelNode(Node):
    def __init__(self, name):
        self.name = name
    def tree_str(self, indent=0):
        return "    " * indent + f"Relation({self.name})"


class SelectNode(Node):
    def __init__(self, cond, child):
        self.cond = cond
        self.child = child
    def tree_str(self, indent=0):
        pad = "    " * indent
        s = pad + f"Select(cond={self.cond.tree_str()})\n"
        s += self.child.tree_str(indent + 1)
        return s


class ProjectNode(Node):
    def __init__(self, attrs, child):
        self.attrs = attrs
        self.child = child
    def tree_str(self, indent=0):
        pad = "    " * indent
        s = pad + f"Project(attrs={self.attrs})\n"
        s += self.child.tree_str(indent + 1)
        return s


class RenameNode(Node):
    def __init__(self, newname, child):
        self.newname = newname
        self.child = child
    def tree_str(self, indent=0):
        pad = "    " * indent
        s = pad + f"Rename(new={self.newname})\n"
        s += self.child.tree_str(indent + 1)
        return s


class SetOpNode(Node):
    def __init__(self, opname, left, right):
        self.opname = opname
        self.left = left
        self.right = right
    def tree_str(self, indent=0):
        pad = "    " * indent
        s = pad + f"{self.opname.capitalize()}(\n"
        s += self.left.tree_str(indent + 1) + "\n"
        s += self.right.tree_str(indent + 1) + "\n"
        s += pad + ")"
        return s


class TimesNode(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def tree_str(self, indent=0):
        pad = "    " * indent
        s = pad + "Times(\n"
        s += self.left.tree_str(indent + 1) + "\n"
        s += self.right.tree_str(indent + 1) + "\n"
        s += pad + ")"
        return s


class JoinNode(Node):
    def __init__(self, cond, left, right):
        self.cond = cond
        self.left = left
        self.right = right
    def tree_str(self, indent=0):
        pad = "    " * indent
        s = pad + f"Join(cond={self.cond.tree_str()})\n"
        s += self.left.tree_str(indent + 1) + "\n"
        s += self.right.tree_str(indent + 1)
        return s


class AndCond(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def tree_str(self, indent=0):
        return f"And({self.left.tree_str()}, {self.right.tree_str()})"


class OrCond(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def tree_str(self, indent=0):
        return f"Or({self.left.tree_str()}, {self.right.tree_str()})"


class NotCond(Node):
    def __init__(self, child):
        self.child = child
    def tree_str(self, indent=0):
        return f"Not({self.child.tree_str()})"


class CmpCond(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right
    def tree_str(self, indent=0):
        opname = {
            "=": "Eq", "!=": "Neq",
            "<": "Lt", "<=": "Leq",
            ">": "Gt", ">=": "Geq",
        }[self.op]
        return f"{opname}({self.left.tree_str()}, {self.right.tree_str()})"


class AttrOperand(Node):
    def __init__(self, qual, name):
        self.qual = qual
        self.name = name
    def tree_str(self, indent=0):
        if self.qual:
            return f"Attr({self.qual}.{self.name})"
        return f"Attr({self.name})"


class NumOperand(Node):
    def __init__(self, value):
        self.value = value
    def tree_str(self, indent=0):
        return f"Num({self.value})"


class StrOperand(Node):
    def __init__(self, value):
        self.value = value
    def tree_str(self, indent=0):
        return f"Str({self.value!r})"


# ============================================================
# PART 3: THE PARSER
# ============================================================

class ParseError(Exception):
    def __init__(self, message, pos):
        self.message = message
        self.pos = pos
        super().__init__(message)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind, what=""):
        tok = self.peek()
        if tok.kind != kind:
            msg = f"expected {what or kind}, got {tok.value!r}"
            raise ParseError(msg, tok.pos)
        return self.advance()

    def parse_query(self):
        node = self.parse_expr()
        if self.peek().kind != "EOF":
            tok = self.peek()
            raise ParseError(f"unexpected token {tok.value!r}", tok.pos)
        return node

    def parse_expr(self):
        return self.parse_union()

    def parse_union(self):
        left = self.parse_intersect()
        while self.peek().kind == "UNION":
            self.advance()
            right = self.parse_intersect()
            left = SetOpNode("union", left, right)
        return left

    def parse_intersect(self):
        left = self.parse_minus()
        while self.peek().kind == "INTERSECT":
            self.advance()
            right = self.parse_minus()
            left = SetOpNode("intersect", left, right)
        return left

    def parse_minus(self):
        left = self.parse_times()
        while self.peek().kind == "MINUS":
            self.advance()
            right = self.parse_times()
            left = SetOpNode("minus", left, right)
        return left

    def parse_times(self):
        left = self.parse_join()
        while self.peek().kind == "TIMES":
            self.advance()
            right = self.parse_join()
            left = TimesNode(left, right)
        return left

    def parse_join(self):
        left = self.parse_primary()
        while self.peek().kind == "JOIN":
            self.advance()
            self.expect("LBRACK", "'['")
            cond = self.parse_condition()
            self.expect("RBRACK", "']'")
            right = self.parse_primary()
            left = JoinNode(cond, left, right)
        return left

    def parse_primary(self):
        tok = self.peek()

        if tok.kind == "SELECT":
            self.advance()
            self.expect("LBRACK", "'['")
            cond = self.parse_condition()
            self.expect("RBRACK", "']'")
            self.expect("LPAREN", "'('")
            child = self.parse_expr()
            self.expect("RPAREN", "')'")
            return SelectNode(cond, child)

        if tok.kind == "PROJECT":
            self.advance()
            self.expect("LBRACK", "'['")
            if self.peek().kind == "RBRACK":
                raise ParseError("empty projection attribute list",
                                 self.peek().pos)
            attrs = [self.expect_ident_text()]
            while self.peek().kind == "COMMA":
                self.advance()
                attrs.append(self.expect_ident_text())
            self.expect("RBRACK", "']'")
            self.expect("LPAREN", "'('")
            child = self.parse_expr()
            self.expect("RPAREN", "')'")
            return ProjectNode(attrs, child)

        if tok.kind == "RENAME":
            self.advance()
            self.expect("LBRACK", "'['")
            newname = self.expect_ident_text()
            self.expect("RBRACK", "']'")
            self.expect("LPAREN", "'('")
            child = self.parse_expr()
            self.expect("RPAREN", "')'")
            return RenameNode(newname, child)

        if tok.kind == "LPAREN":
            self.advance()
            inner = self.parse_expr()
            self.expect("RPAREN", "')'")
            return inner

        if tok.kind == "IDENT" or tok.value in KEYWORDS:
            self.advance()
            return RelNode(tok.value)

        raise ParseError(f"expected expression, got {tok.value!r}", tok.pos)

    def expect_ident_text(self):
        tok = self.peek()
        if tok.kind == "IDENT" or tok.value in KEYWORDS:
            self.advance()
            return tok.value
        raise ParseError(f"expected identifier, got {tok.value!r}", tok.pos)

    def parse_condition(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.peek().kind == "OR":
            self.advance()
            right = self.parse_and()
            left = OrCond(left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek().kind == "AND":
            self.advance()
            right = self.parse_not()
            left = AndCond(left, right)
        return left

    def parse_not(self):
        if self.peek().kind == "NOT":
            self.advance()
            return NotCond(self.parse_not())
        return self.parse_cmp()

    def parse_cmp(self):
        if self.peek().kind == "LPAREN":
            self.advance()
            inner = self.parse_condition()
            self.expect("RPAREN", "')'")
            return inner
        left = self.parse_operand()
        op_tok = self.peek()
        op_map = {
            "EQ": "=", "NEQ": "!=", "LT": "<",
            "LEQ": "<=", "GT": ">", "GEQ": ">=",
        }
        if op_tok.kind not in op_map:
            raise ParseError(
                f"expected comparison operator, got {op_tok.value!r}",
                op_tok.pos)
        self.advance()
        right = self.parse_operand()
        return CmpCond(op_map[op_tok.kind], left, right)

    def parse_operand(self):
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.advance()
            return NumOperand(int(tok.value))
        if tok.kind == "STRING":
            self.advance()
            return StrOperand(tok.value)
        if tok.kind == "IDENT" or tok.value in KEYWORDS:
            self.advance()
            first = tok.value
            if self.peek().kind == "DOT":
                self.advance()
                second = self.expect_ident_text()
                return AttrOperand(first, second)
            return AttrOperand(None, first)
        raise ParseError(f"expected operand, got {tok.value!r}", tok.pos)


# ============================================================
# PART 4: THE EVALUATOR
# ============================================================

class EvalError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class Table:
    def __init__(self, schema, rows):
        self.schema = schema
        self.rows = rows

    def copy(self):
        return Table(list(self.schema), list(self.rows))


counters = {
    "join_comparisons": 0,
    "select_checks": 0,
}


def reset_counters():
    counters["join_comparisons"] = 0
    counters["select_checks"] = 0


def as_set(rows):
    return set(rows)


def evaluate(node, env):
    if isinstance(node, RelNode):
        if node.name not in env:
            raise EvalError(f"unknown relation {node.name!r}")
        return env[node.name].copy()

    if isinstance(node, SelectNode):
        child = evaluate(node.child, env)
        out_rows = []
        for row in child.rows:
            counters["select_checks"] += 1
            if eval_condition(node.cond, row, child.schema, env):
                out_rows.append(row)
        return Table(list(child.schema), out_rows)

    if isinstance(node, ProjectNode):
        child = evaluate(node.child, env)
        indices = []
        for name in node.attrs:
            idx = find_attr(child.schema, name)
            if idx is None:
                raise EvalError(f"unknown attribute {name!r}")
            indices.append(idx)
        new_schema = [child.schema[i] for i in indices]
        seen = set()
        out_rows = []
        for row in child.rows:
            new_row = tuple(row[i] for i in indices)
            if new_row not in seen:
                seen.add(new_row)
                out_rows.append(new_row)
        return Table(new_schema, out_rows)

    if isinstance(node, RenameNode):
        child = evaluate(node.child, env)
        new_schema = [(node.newname, a) for (_, a) in child.schema]
        return Table(new_schema, list(child.rows))

    if isinstance(node, SetOpNode):
        left = evaluate(node.left, env)
        right = evaluate(node.right, env)
        check_union_compatible(left, right, node.opname)
        lset = as_set(left.rows)
        rset = as_set(right.rows)
        if node.opname == "union":
            result = lset | rset
        elif node.opname == "intersect":
            result = lset & rset
        else:
            result = lset - rset
        return Table(list(left.schema), list(result))

    if isinstance(node, TimesNode):
        left = evaluate(node.left, env)
        right = evaluate(node.right, env)
        new_schema = list(left.schema) + list(right.schema)
        check_schema_no_dupes(new_schema)
        out_rows = []
        for lr in left.rows:
            for rr in right.rows:
                out_rows.append(tuple(lr) + tuple(rr))
        return Table(new_schema, out_rows)

    if isinstance(node, JoinNode):
        left = evaluate(node.left, env)
        right = evaluate(node.right, env)
        new_schema = list(left.schema) + list(right.schema)
        check_schema_no_dupes(new_schema)
        out_rows = []
        for lr in left.rows:
            for rr in right.rows:
                counters["join_comparisons"] += 1
                combined = tuple(lr) + tuple(rr)
                if eval_condition(node.cond, combined, new_schema, env):
                    out_rows.append(combined)
        return Table(new_schema, out_rows)

    raise EvalError(f"unknown node type {type(node).__name__}")


# ------------------------------------------------------------
# find_attr(schema, name) -> index or None
# ------------------------------------------------------------
# CASE-INSENSITIVE lookup. "R.b", "R.B", "r.b" all match.
# ------------------------------------------------------------

def find_attr(schema, name):
    if "." in name:
        rel, attr = name.split(".", 1)
        matches = [i for i, (r, a) in enumerate(schema)
                   if r.lower() == rel.lower() and a.lower() == attr.lower()]
    else:
        matches = [i for i, (_, a) in enumerate(schema)
                   if a.lower() == name.lower()]
    if len(matches) == 0:
        return None
    if len(matches) > 1:
        raise EvalError(f"ambiguous attribute {name!r}")
    return matches[0]


def check_schema_no_dupes(schema):
    seen = set()
    for q in schema:
        if q in seen:
            raise EvalError(f"duplicate attribute name {q[0]}.{q[1]}")
        seen.add(q)


def check_union_compatible(a, b, opname):
    if len(a.schema) != len(b.schema):
        raise EvalError(
            f"{opname}: different number of attributes "
            f"({len(a.schema)} vs {len(b.schema)})")
    for (ra, aa), (rb, ab) in zip(a.schema, b.schema):
        if aa.lower() != ab.lower():
            raise EvalError(
                f"{opname}: attribute name mismatch "
                f"({aa!r} vs {ab!r})")


def eval_condition(cond, row, schema, env):
    if isinstance(cond, AndCond):
        return eval_condition(cond.left, row, schema, env) and \
               eval_condition(cond.right, row, schema, env)
    if isinstance(cond, OrCond):
        return eval_condition(cond.left, row, schema, env) or \
               eval_condition(cond.right, row, schema, env)
    if isinstance(cond, NotCond):
        return not eval_condition(cond.child, row, schema, env)
    if isinstance(cond, CmpCond):
        lv = eval_operand(cond.left, row, schema, env)
        rv = eval_operand(cond.right, row, schema, env)
        if isinstance(lv, int) != isinstance(rv, int):
            raise EvalError(
                f"type mismatch: cannot compare "
                f"{type_name(lv)} to {type_name(rv)}")
        return apply_cmp(cond.op, lv, rv)
    raise EvalError("bad condition node")


def type_name(v):
    return "number" if isinstance(v, int) else "string"


def apply_cmp(op, a, b):
    if op == "=":  return a == b
    if op == "!=": return a != b
    if op == "<":  return a < b
    if op == "<=": return a <= b
    if op == ">":  return a > b
    if op == ">=": return a >= b
    raise EvalError(f"unknown comparison op {op!r}")


def eval_operand(op, row, schema, env):
    if isinstance(op, NumOperand):
        return op.value
    if isinstance(op, StrOperand):
        return op.value
    if isinstance(op, AttrOperand):
        if op.qual:
            full = f"{op.qual}.{op.name}"
        else:
            full = op.name
        idx = find_attr(schema, full)
        if idx is None:
            raise EvalError(f"unknown attribute {full!r}")
        return row[idx]
    raise EvalError("bad operand node")


# ============================================================
# PART 5: RELATION DEFINITION PARSING
# ============================================================

def parse_relation_defs(source):
    tokens = tokenize(source)
    env = {}
    i = 0

    while i < len(tokens):
        tok = tokens[i]
        if tok.kind == "EOF":
            break

        if tok.kind != "IDENT":
            raise ParseError(
                f"expected relation name, got {tok.value!r}", tok.pos)
        relname = tok.value
        i += 1

        if tokens[i].kind != "LPAREN":
            raise ParseError(
                f"expected '(' after relation name", tokens[i].pos)
        i += 1

        attrs = []
        while tokens[i].kind != "RPAREN":
            if tokens[i].kind == "IDENT" or tokens[i].value in KEYWORDS:
                attrs.append(tokens[i].value)
                i += 1
            else:
                raise ParseError(
                    f"expected attribute name, got {tokens[i].value!r}",
                    tokens[i].pos)
            if tokens[i].kind == "COMMA":
                i += 1
        i += 1

        if tokens[i].kind != "EQ":
            raise ParseError(
                f"expected '=' after attribute list", tokens[i].pos)
        i += 1

        if tokens[i].kind != "LBRACE":
            raise ParseError(
                f"expected '{{' before tuples", tokens[i].pos)
        i += 1

        rows = []
        while tokens[i].kind != "RBRACE":
            vals = []
            for _ in range(len(attrs)):
                t = tokens[i]
                if t.kind == "NUMBER":
                    vals.append(int(t.value))
                elif t.kind == "STRING":
                    vals.append(t.value)
                elif t.kind == "IDENT":
                    vals.append(t.value)
                elif t.value in KEYWORDS:
                    vals.append(t.value)
                else:
                    raise ParseError(
                        f"expected value, got {t.value!r}", t.pos)
                i += 1
                if tokens[i].kind == "COMMA":
                    i += 1
            rows.append(tuple(vals))
        i += 1

        schema = [(relname, a) for a in attrs]
        seen = set()
        uniq = []
        for r in rows:
            if r not in seen:
                seen.add(r)
                uniq.append(r)
        env[relname] = Table(schema, uniq)

    return env


# ============================================================
# PART 6: THE CLI
# ============================================================

import sys
import time


def print_table(t):
    names = [f"{r}.{a}" if r else a for (r, a) in t.schema]
    print(" | ".join(names))
    print("-" * 40)
    for row in t.rows:
        print(" | ".join(str(v) for v in row))
    print(f"({len(t.rows)} tuples)")


def main():
    args = sys.argv[1:]
    tree_only = False
    data_file = None
    show_time = False
    quiet = False
    query = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--tree":
            tree_only = True
            i += 1
        elif a == "--data":
            data_file = args[i + 1]
            i += 2
        elif a == "--time":
            show_time = True
            i += 1
        elif a == "--quiet":
            quiet = True
            i += 1
        else:
            query = a
            i += 1

    if query is None:
        print("usage: ra.py [--tree] [--data FILE] [--time] [--quiet] QUERY")
        return

    env = {}
    if data_file:
        try:
            with open(data_file) as f:
                env = parse_relation_defs(f.read())
        except (ParseError, TokenError) as e:
            print(f"data file error: {e.message}")
            return
        except FileNotFoundError:
            print(f"data file error: file not found: {data_file}")
            return

    try:
        toks = tokenize(query)
    except TokenError as e:
        print(f"lex error at {e.pos}: {e.message}")
        return

    try:
        tree = Parser(toks).parse_query()
    except ParseError as e:
        print(f"syntax error at {e.pos}: {e.message}")
        return

    if tree_only:
        print(tree.tree_str())
        return

    reset_counters()
    t0 = time.perf_counter()
    try:
        result = evaluate(tree, env)
    except EvalError as e:
        print(f"eval error: {e.message}")
        return
    t1 = time.perf_counter()

    if not quiet:
        print_table(result)
    print(f"join comparisons: {counters['join_comparisons']}")
    print(f"select checks: {counters['select_checks']}")
    if show_time:
        print(f"time: {t1 - t0:.6f} s")


if __name__ == "__main__":
    main()