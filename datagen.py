# datagen.py — writes a fake dataset with R(a,b) and S(b,c)

import sys
import random

def gen(n, match_rate, outfile):
    # R(a, b): n tuples. a = random, b = value in [0, B) where
    # B is chosen so that S has ~ n tuples with b values that
    # match roughly match_rate of R's rows.
    #
    # Trick: make S's b values drawn from a small set of size
    # B = n / match_rate. Then each R row matches ~ match_rate
    # S rows on average (since each S.b picks one of B values).
    B = max(1, n // max(1, match_rate))

    lines = []
    lines.append(f"R(A, B) = {{")
    for i in range(n):
        a = random.randint(0, 1_000_000)
        b = random.randint(0, B - 1)
        lines.append(f"  {a}, {b}")
    lines.append("}")
    lines.append("")

    lines.append(f"S(B, C) = {{")
    for i in range(n):
        b = random.randint(0, B - 1)
        c = random.randint(0, 1_000_000)
        lines.append(f"  {b}, {c}")
    lines.append("}")

    with open(outfile, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    n = int(sys.argv[1])
    mr = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out = sys.argv[3] if len(sys.argv) > 3 else "data.txt"
    gen(n, mr, out)
    print(f"wrote {out}: n={n}, match_rate={mr}")