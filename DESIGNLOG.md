# Design Log

## 2026-09-20
Tried: sketching the EBNF by hand.
What broke: I initially wrote `Expr ::= Expr "union" Expr` and
realized my recursive descent parser would infinite-loop. Rewrote
as iteration with `{ }` repetition. So much debugging... my least favourite.

## 2026-09-30
Tried: getting case 8 (`select[union=3](R)`) to work.
What broke: my parser had "if token.kind == UNION: treat as operator"
everywhere. It never considered that `union` could be an identifier.
Fixed by adding a separate `expect_ident_text()` helper that accepts
any identifier-shaped token regardless of keyword status.
I found this by running the test suite, case 8 was producing a
syntax error.

## 2026-09-30
Asked AI to write the tokenizer. It used `re.findall()` for the
whole thing. That violates the "no regex" rule. Rewrote as a
character-by-character loop.

## 2026-09-30
Asked AI about maximal munch. It said "check for <= before <"
but didn't mention that the SAME logic applies to >= and !=.
I caught this by writing case 4 (`Age>-30`) and seeing the
scanner produce `>` then `-30` instead of `>-` and `30`.
Once I saw it worked there, I made sure all two-char ops were
checked in the same place.

## 2026-09-30
AI apparently doesnt like using proper formatting, and when asking it to debug a segment... it broke everything and I spent ages trying to figure out what on earth was wrong originally.