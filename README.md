# Relational Algebra Engine (COMP 3005 Bonus Project 1)

## What it is
A baby database engine. You write queries in a SQL-sortof syntax,
it parses them by hand (no regex, no parser generators), and
evaluates them with nested loops.

## How to run

    # Print the parse tree for a query (no data needed):
    python ra.py --tree "project[Name](select[Age>30](Employees))"

    # Run a query against a data file:
    python ra.py --data mydata.txt "select[Age>30](Employees)"

    # Time a query:
    python ra.py --data mydata.txt --time "R join[R.B=S.B] S"

## Data file format

    Employees (EID, Name, Age, DID) = {
      E1, John, 32, D1
      E2, Alice, 28, D2
    }

- Each attribute is an identifier.
- Values are numbers or strings.
- A bare word is a string.
- A string with spaces/commas/quotes MUST be quoted with '...'.
- Inside quotes, '' means one literal quote.
- Lines starting with // are comments.

## Supported syntax

    select[<cond>](<expr>)
    project[<attrs>](<expr>)
    rename[<newname>](<expr>)

    <expr> union     <expr>
    <expr> intersect <expr>
    <expr> minus     <expr>
    <expr> times     <expr>
    <expr> join[<cond>] <expr>

## Precedence (lowest → highest)
union, intersect, minus, times, join, select/project/rename/parens

All binary operators are left-associative.

## Known limitations
- No nulls. Every attribute has a value.
- Everything is in memory. No disk I/O.
- Nested loops only. No hash join, no sort-merge.
- No query optimization; the tree is executed exactly as written.
- Self-join requires rename to disambiguate.

## Why self-join needs rename
Query: `rename[E2](Emp) join[Emp.MgrID=E2.EID] Emp`

Without rename, both copies of Emp have the same relation name.
Attributes like Emp.EID would be ambiguous — did you mean the
manager's EID or the employee's? Rename gives one copy a new
name so Emp.EID and E2.EID mean different things.

## Heres an example of what went in my terminal:

python3 datagen.py 1000 1 data_1000.txt
python3 datagen.py 2000 1 data_2000.txt
python3 datagen.py 4000 1 data_4000.txt
python3 datagen.py 8000 1 data_8000.txt
python3 datagen.py 16000 1 data_16000.txt
python3 datagen.py 32000 1 data_32000.txt
python3 datagen.py 64000 1 data_64000.txt

python3 ra.py --data data_1000.txt --time --quiet "R join[R.B=S.B] S"
python3 ra.py --data data_2000.txt --time --quiet "R join[R.B=S.B] S"
python3 ra.py --data data_4000.txt --time --quiet "R join[R.B=S.B] S"
python3 ra.py --data data_8000.txt --time --quiet "R join[R.B=S.B] S"
python3 ra.py --data data_16000.txt --time --quiet "R join[R.B=S.B] S"
python3 ra.py --data data_32000.txt --time --quiet "R join[R.B=S.B] S"
python3 ra.py --data data_64000.txt --time --quiet "R join[R.B=S.B] S"


## NOTE:

AI was a fantastic tool for formatting my ideas, and cleaning up code. The pretty formatting of this file, DESIGNLOG, and REPORT, are not my work. # COMP3005-Bonus1
