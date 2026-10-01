# GRAMMAR.md

## 1. The Grammar (EBNF)

Below is the complete grammar for the query language and for relation
definitions. It uses EBNF notation: { X } means zero or more repetitions
of X, [ X ] means optional, | means alternation, and quoted strings are
literal terminals.

### Top-level program

    Program       ::= { RelationDef | Comment | BlankLine }

### Relation definitions

    RelationDef   ::= IDENT "(" IdentList ")" "=" "{" TupleList "}"
    IdentList     ::= IDENT { "," IDENT }
    TupleList     ::= { TupleLine }
    TupleLine     ::= Value { "," Value }

### Queries

    Query         ::= Expr

### Expressions, from lowest to highest precedence

    Expr          ::= UnionExpr
    UnionExpr     ::= IntersectExpr { "union" IntersectExpr }
    IntersectExpr ::= MinusExpr { "intersect" MinusExpr }
    MinusExpr     ::= TimesExpr { "minus" TimesExpr }
    TimesExpr     ::= JoinExpr { "times" JoinExpr }
    JoinExpr      ::= PrimaryExpr { "join" "[" Condition "]" PrimaryExpr }

### Primary expressions

    PrimaryExpr   ::= "select" "[" Condition "]" "(" Expr ")"
                    | "project" "[" AttrList "]" "(" Expr ")"
                    | "rename" "[" IDENT "]" "(" Expr ")"
                    | "(" Expr ")"
                    | IDENT

    AttrList      ::= IDENT { "," IDENT }

### Conditions

    Condition     ::= OrCond
    OrCond        ::= AndCond { "or" AndCond }
    AndCond       ::= NotCond { "and" NotCond }
    NotCond       ::= "not" NotCond | CmpCond
    CmpCond       ::= "(" Condition ")" | Comparison
    Comparison    ::= Operand CmpOp Operand
    CmpOp         ::= "=" | "!=" | "<" | "<=" | ">" | ">="
    Operand       ::= NUMBER | STRING | QualifiedName
    QualifiedName ::= IDENT [ "." IDENT ]

### Literals

    IDENT         ::= Letter { Letter | Digit | "_" }
    NUMBER        ::= ["-"] Digit { Digit }
    STRING        ::= "'" { AnyCharExceptQuote | "''" } "'"
                    | BareWord
    BareWord      ::= (any run of characters excluding comma, parenthesis,
                       space, and quote)

---

## 2. Precedence and Associativity

Precedence for the binary set operators and join, from loosest to
tightest:

    union       (level 1, left-associative)
    intersect   (level 2, left-associative)
    minus       (level 3, left-associative)
    times       (level 4, left-associative)
    join        (level 5, left-associative)
    select, project, rename, and parentheses  (level 6, highest)

Precedence for conditions, from loosest to tightest:

    or          (level 1, left-associative)
    and         (level 2, left-associative)
    not         (level 3, prefix, right-associative)
    =, !=, <, <=, >, >=   (level 4, non-associative)
    parentheses (level 5, highest)

Consequences for grouping:

- A union B minus C parses as A union (B minus C), because minus binds
  tighter than union.
- A minus B minus C parses as (A minus B) minus C, because minus is
  left-associative.
- not (a=1 and b=2) or c>3 parses as (not (a=1 and b=2)) or (c>3),
  because not binds tighter than and, which binds tighter than or.
- a=1 and b=2 or c=3 parses as (a=1 and b=2) or (c=3).

These choices are enforced by the grammar rules in section 1, not by
special cases inside the parser.

---

## 3. Ambiguity Demonstration

Consider the following naive grammar:

    Expr ::= Expr "union" Expr
           | Expr "minus" Expr
           | "(" Expr ")"
           | IDENT

Take the input A union B minus C. This grammar produces at least two
different parse trees for that input.

Tree 1 treats minus as binding tighter, equivalent to:

    A union (B minus C)

Tree 2 treats the operators as evaluating left to right, equivalent to:

    (A union B) minus C

The two groupings produce different results on the same data. Consider:

    A = { 1 }
    B = { 2 }
    C = { 1 }

Under Tree 1:

    A union (B minus C)
    = { 1 } union ( { 2 } minus { 1 } )
    = { 1 } union { 2 }
    = { 1, 2 }

Under Tree 2:

    (A union B) minus C
    = ( { 1 } union { 2 } ) minus { 1 }
    = { 1, 2 } minus { 1 }
    = { 2 }

The results { 1, 2 } and { 2 } are not equal. The naive grammar is
therefore genuinely ambiguous: the choice of parse tree changes the
answer, not just the internal representation.

The stratified grammar shown in section 1 removes the ambiguity. It
assigns union, intersect, minus, times, and join to five distinct
precedence levels, each one tighter than the last. In that grammar,
A union B minus C has exactly one parse tree, the one corresponding
to Tree 1 above. Tree 2 is not derivable from the stratified grammar.

The structural change that removes the ambiguity is that the left-hand
side of each binary operator rule is no longer Expr but the next-tighter
level. UnionExpr can only appear where a union is syntactically allowed,
and its operands must be IntersectExpr, which cannot contain a bare
minus at the top level. That restriction is what eliminates Tree 2.

---

## 4. Parsing Strategy

I used recursive descent. Each rule in the grammar corresponds to one
method on the Parser class, and those methods call each other according
to the precedence chain. parse_expr calls parse_union, which calls
parse_intersect, which calls parse_minus, and so on down to parse_primary.
Conditions have their own chain: parse_condition calls parse_or, which
calls parse_and, which calls parse_not, which calls parse_cmp, which
calls parse_operand.

Recursive descent was chosen for three reasons.

First, it matches the grammar one to one. Each method is a direct
translation of one rule, so the code is easy to defend against this
document during the oral check.

Second, it handles the precedence chain naturally. Stratifying the
grammar into levels makes the parser's call graph mirror the precedence
table exactly.

Third, it gives good error messages. When a token is unexpected, the
parser knows exactly which rule it was inside, so it can report what
was expected and where.

### Left recursion

The naive grammar from section 3 is left-recursive: the rule
Expr ::= Expr "union" Expr has Expr as the first symbol on the
right-hand side. A recursive descent parser cannot handle this rule
as written, because parse_expr would call itself immediately without
consuming any input and recurse forever.

I removed left recursion by rewriting each binary rule in iterative
form. Instead of:

    UnionExpr ::= UnionExpr "union" IntersectExpr
                | IntersectExpr

the grammar uses:

    UnionExpr ::= IntersectExpr { "union" IntersectExpr }

The braces in EBNF mean zero or more repetitions. In the parser, this
becomes a while loop: parse the first operand, then while the next
token is union, consume it, parse another operand, and combine. Because
the left-hand side of the rule is no longer UnionExpr, the parser never
recurses on itself without consuming input. The same rewrite is applied
to intersect, minus, times, and join.

### Maximal munch in the tokenizer

The tokenizer implements maximal munch: on seeing >, it checks the next
character before deciding whether it emitted > or >=. The two-character
operators !=, <=, and >= are checked before the single-character
operators =, <, and >.

This matters for inputs like Age>-30, where the tokens must be > and
-30, not >- and 30. My scanner handles this correctly because >- is not
in the two-character operator table, so the scanner falls through to
the single-character > branch and leaves the -30 to be scanned as a
number on the next iteration.

---

## 5. Keyword vs Identifier Rule

The input select[union=3](R) uses the keyword union as an attribute
name. To support this, the parser accepts any identifier-shaped token
as an identifier when it is in a position that expects an identifier,
for instance inside an attribute list, as a relation name, or as an
operand in a condition. The token kind produced by the scanner (for
example UNION) is only treated as an operator when the parser is in
a position that expects an operator.

Concretely, the helper method expect_ident_text accepts a token whose
kind is IDENT or whose text matches any keyword. It is used everywhere
the grammar expects an IDENT. The operator branches (parse_union,
parse_and, and so on) only look at the token kind. So the same word
can be read as an operator or as an identifier depending on grammatical
position, and the parser disambiguates without any special-case rules
in the scanner.

Additionally, attribute names and relation names are matched
case-insensitively during evaluation. R.b, R.B, and r.b all resolve to
the same column. This rule is stated here so it is part of the language
definition rather than an implementation detail.

---

## 6. Sources

- Bob Nystrom, Crafting Interpreters, chapters on scanning and parsing
  (free online at craftinginterpreters.com).
- Wikipedia articles on EBNF, recursive descent parsing, maximal munch,
  and operator precedence.
- Aho, Lam, Sethi, Ullman, Compilers: Principles, Techniques, and Tools
  (the Dragon Book), sections 2.2 through 2.4 and section 4.4, for the
  formal treatment of context-free grammars, ambiguity, and top-down
  parsing.

### Where AI assistance was wrong

When I first asked for help with the tokenizer, one suggested
implementation used Python's re module to split the input on a large
alternation of patterns. That violates the rule that no regular
expression library may be used anywhere in the tokenizer or parser.
I rewrote the tokenizer as a character-by-character scanner with a
single dispatch chain.

When I asked about maximal munch, one response only discussed <= and <,
without mentioning that the same logic applies to >=, !=, and any other
multi-character operator. I noticed this by testing the input Age>-30
and confirming the scanner produced > and -30 rather than >- and 30.
Once I saw the rule generalizes, I made sure all multi-character
operators went through the same two-character lookup table.

When I asked about grammar ambiguity, one response claimed that
left-associativity and right-associativity could be handled by setting
a boolean flag on each operator at parse time, without changing the
grammar. That is not true: associativity is a property of the grammar's
structure, expressed by whether each binary rule is left-recursive or
right-recursive, and encoding it as a runtime flag would not produce
distinct parse trees for the two cases. The correct fix is the grammar
rewrite described in section 3.