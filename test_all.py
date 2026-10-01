# tests/test_all.py — run all 25 required cases.

import subprocess
import sys
import os

# We run ra.py as a subprocess so we test the actual CLI.
HERE = os.path.dirname(os.path.abspath(__file__))
RA = os.path.join(HERE, "..", "ra.py")

DATA = """
Employees (EID, Name, Age, DID) = {
  E1, John, 32, D1
  E2, Alice, 28, D2
  E3, Bob, 29, D1
}
A (x) = { 1 2 3 }
B (x) = { 2 3 4 }
C (x) = { 1 }
R (a, b) = { 1, 2  2, 3  3, 3 }
S (b, c) = { 2, 10  3, 20 }
"""

def write_data(tmpfile):
    with open(tmpfile, "w") as f:
        f.write(DATA)

def run(args):
    p = subprocess.run(
        [sys.executable, RA] + args,
        capture_output=True, text=True)
    return p.stdout + p.stderr

def main():
    import tempfile
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    write_data(tmp.name)
    tmp.close()

    cases = [
        # 1: no whitespace at all
        (["--data", tmp.name, "--tree", "select[x1=3](R)"], "Relation(R)"),
        # 2: same tree as 1
        (["--data", tmp.name, "--tree", "select[ x1 = 3 ](R)"], "Relation(R)"),
        # 3: >= is one token
        (["--data", tmp.name, "--tree", "select[Age>=30](Employees)"], "Geq"),
        # 4: > then -30
        (["--data", tmp.name, "--tree", "select[Age>-30](Employees)"], "Gt"),
        # 5: paren inside string
        (["--data", tmp.name, "select[Name='Bob)'](Employees)"], "0 tuples"),
        # 6: comma inside string
        (["--data", tmp.name, "select[Name='a,b'](Employees)"], "0 tuples"),
        # 7: doubled quote
        (["--data", tmp.name, "select[Name='O''Brien'](Employees)"], "0 tuples"),
        # 8: keyword as attribute
        (["--data", tmp.name, "--tree", "select[union=3](R)"], "Relation(R)"),
        # 9: unterminated string
        (["--data", tmp.name, "select[Name='Bob](Employees)"], "unterminated"),
        # 10: precedence union vs minus
        (["--data", tmp.name, "--tree", "A union B minus C"], "SetOpNode"),
        # 11: left-assoc minus
        (["--data", tmp.name, "--tree", "A minus B minus C"], "Minus"),
        # 12: not binds tighter than and
        (["--data", tmp.name, "--tree",
          "select[not (a=1 and b=2) or c>3](R)"], "Or"),
        # 13: and binds tighter than or
        (["--data", tmp.name, "--tree",
          "select[a=1 and b=2 or c=3](R)"], "Or"),
        # 14: three levels of nesting
        (["--data", tmp.name,
          "project[Name](select[Age>30](select[DID='D1'](Employees)))"],
         "John"),
        # 15: explicit parens
        (["--data", tmp.name, "--tree",
          "(A union B) minus (C intersect D)"], "Minus"),
        # 16: missing paren
        (["--data", tmp.name, "select[Age>30](R"], "syntax error"),
        # 17: empty projection
        (["--data", tmp.name, "project[](R)"], "empty projection"),
        # 18: column=column comparison
        (["--data", tmp.name, "select[A=B](R)"], "3 tuples"),
        # 19: qualified join
        (["--data", tmp.name, "--tree",
          "Emp join[Emp.DID=Dept.DID] Dept"], "Join"),
        # 20: self-join with rename
        (["--data", tmp.name, "--tree",
          "rename[E2](Emp) join[Emp.MgrID=E2.EID] Emp"], "Join"),
        # 21: union-incompatible
        (["--data", tmp.name, "A union Employees"], "mismatch"),
        # 22: type error
        (["--data", tmp.name, "select[Age>'30'](Employees)"], "type mismatch"),
        # 23: projection removes dupes
        (["--data", tmp.name, "project[DID](Employees)"], "2 tuples"),
        # 24: project[Name, Name]
        (["--data", tmp.name, "project[Name, Name](Employees)"], "Name"),
        # 25: empty result prints schema
        (["--data", tmp.name, "select[Age>100](Employees)"], "0 tuples"),
    ]

    passed = 0
    for idx, (args, expect) in enumerate(cases, 1):
        out = run(args)
        ok = expect in out
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        print(f"[{status}] case {idx:2d}: expect {expect!r}")
        if not ok:
            print(f"        got: {out[:200]!r}")

    print(f"\n{passed}/{len(cases)} passed")
    os.unlink(tmp.name)

if __name__ == "__main__":
    main()