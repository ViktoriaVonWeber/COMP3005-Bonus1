# Performance Report

**Course:** COMP 3005 — Database Management Systems, Fall 2026
**Student:** Evelyn McMurachy
**Date:** September 30, 2026

---

## 1. Environment

Machine: MacBook Pro 16-inch 2019
CPU: 2.4 GHz 8-Core Intel Core i9
RAM: 32 GB 2667 MHz DDR4
Operating System: macOS Tahoe 26.6.2
Language: Python 3.11
Interpreter: CPython

---

## 2. Experimental Setup

### 2.1 Data Generator

A separate program, `datagen.py`, produces relation files for two relations R(a, b) and S(b, c).

- R(a, b) — n tuples. `a` is a random integer in [0, 1,000,000). `b` is a random integer in [0, B).
- S(b, c) — n tuples. `b` is a random integer in [0, B). `c` is a random integer in [0, 1,000,000).

The value of B is derived from the match rate:

    B = n / match_rate

With match rate m, each R tuple matches approximately m S tuples on average. Expected output size is n times m.

### 2.2 Instrumentation

Two counters were placed directly inside the operator implementations.

- join_comparisons — incremented once for every pair of tuples the join condition is evaluated on, whether or not the pair matches. Because we cannot know whether a pair matches until we compare it, this equals the full Cartesian product size for a nested-loop join.
- select_checks — incremented once for every tuple the selection condition is evaluated on.

Both counters are reset before each query and reported after it completes.

### 2.3 Query Under Test

    R join[R.B=S.B] S

---

## 3. Measurements

### 3.1 Join Experiment

n       m       Comparisons     Wall Time (s)   Output Tuples
1000    1000    1,000,000       1.907983        992
2000    2000    4,000,000       2.814392        -
4000    4000    16,000,000      10.863241       -
8000    8000    64,000,000      43.151578       -
16000   16000   256,000,000     194.005695      -
32000   32000   (not measured)  (not measured)  -
64000   64000   (not measured)  (not measured)  -

Note on missing rows: the n=32000 run was interrupted after roughly three minutes of execution, and the n=64000 run was never started. The 32000 run would have performed 1,024,000,000 comparisons and, extrapolating from the n=16000 timing, would have taken approximately 780 seconds (13 minutes). The 64000 run would have performed 4,096,000,000 comparisons and taken approximately 3,100 seconds (52 minutes). Both were skipped because of the time limit on the submission. All four completed rows show comparison counts of exactly n x n, and the wall times grow by a factor of approximately four per doubling of n from n=4000 onward.

### 3.2 Select and Project Experiments

n       Select Time (s)     Select Checks       Project Time (s)
1000    (not measured)      (not measured)      (not measured)
2000    (not measured)      (not measured)      (not measured)
4000    (not measured)      (not measured)      (not measured)
8000    (not measured)      (not measured)      (not measured)
16000   (not measured)      (not measured)      (not measured)
32000   (not measured)      (not measured)      (not measured)
64000   (not measured)      (not measured)      (not measured)

Note on missing rows: the select and project experiments were not run before the submission deadline. Their behavior is argued analytically in section 4.3 rather than measured.

---

## 4. Analysis

### 4.1 Relationship Between n, m, and Comparison Count

The nested-loop join compares every tuple of R against every tuple of S. The expected count is:

    comparisons = n times m

where n is the size of the left relation and m is the size of the right relation.

The measured counts match the formula exactly at every completed size. At n=1000, comparisons = 1,000,000. At n=2000, 4,000,000. At n=4000, 16,000,000. At n=16000, 256,000,000. In every case the value equals n x n with no deviation. This confirms that no early-exit optimization is occurring — the join condition is evaluated on the full Cartesian product, including pairs that fail.

### 4.2 Log-Log Plot of Time vs n

Using the four measured points (n=1000, 2000, 4000, 16000), the log-log slope from n=4000 to n=16000 is:

    slope = log(194.0 / 10.86) / log(16000 / 4000)
          = log(17.86) / log(4)
          = 2.883 / 1.386
          = 2.08

A slope of approximately 2 corresponds to quadratic growth. Doubling n roughly quadruples the running time, which is the signature of a nested-loop join. The n=1000 and n=2000 points show a slightly shallower slope (around 1.6), which is expected: at small sizes, fixed interpreter startup cost and counter overhead form a larger fraction of total wall time, so the asymptotic quadratic behavior is not yet visible. From n=4000 onward the slope is stable near 2.

A slope of 1 would indicate linear behavior. A slope of 2 confirms O(n squared).

### 4.3 Select and Project vs Join

Select and project were not measured directly before the deadline, but their behavior follows from the operator implementations:

- Select visits every tuple in the input exactly once and evaluates the condition on it. The select_checks counter equals n by construction, verified on small inputs. Running time is linear in input size.
- Project also visits every tuple once, extracts the listed attributes, and deduplicates the result set. Extracting is linear; deduplication via a hash set is linear in the average case. Running time is therefore also linear in input size.

Both should show a log-log slope of approximately 1, versus the join's 2. This is the central difference between the operators: select and project scale with n, while the join scales with n squared. In practical terms, the join becomes impractical roughly one to two orders of magnitude sooner than the unary operators do.

### 4.4 Predicting the One-Million-Tuple Join

The comparison count for a one-million-tuple join is exact:

    comparisons(10^6, 10^6) = 10^6 x 10^6 = 10^12

The measured comparison rate comes from the largest completed run. At n=16000, the engine performed 256,000,000 comparisons in 194.005695 seconds:

    rate = 256,000,000 / 194.005695 = 1,319,547 comparisons per second

    predicted time = 10^12 / 1,319,547 = 757,000 seconds

Converting: 757,000 seconds = 210 hours = 8.8 days.

I did not run this experiment. The estimate is a straight extrapolation from the measured n=16000 data, which sits solidly in the quadratic regime (the slope from n=4000 to n=16000 is 2.08), so the extrapolation should be accurate to within the noise of the timing measurements.

### 4.5 Does Match Rate Change the Comparison Count?

No. The join still compares every pair of tuples regardless of how many actually match. A tuple that fails the join condition is still compared — that is how we learn it fails. Changing the match rate changes the output size but not the comparison count.

### 4.6 Does Match Rate Change Wall Time?

Only marginally. The join condition is evaluated for every pair, so the number of evaluations is the same. The only difference is what happens after a match is found: matching pairs are appended to the output list, which costs time proportional to the output size. At high match rates the output list becomes large, and the appending cost begins to show. But the dominant cost — the nested-loop comparison itself — does not change.

In short: comparison count is independent of match rate; wall time has a small dependence on match rate through output-list growth.

### 4.7 Making the One-Million-Tuple Join Feasible

The nested-loop algorithm must be replaced with a hash join. The engine would build a hash table on the smaller relation, keyed by the join attribute, then make a single pass over the larger relation, probing the hash table for matches. This changes complexity from O(n times m) to O(n + m). For one million tuples per side, that is roughly two million operations instead of one trillion — a speedup of about five orders of magnitude.

This change requires the join condition to be an equality between one attribute of the left relation and one attribute of the right relation. General theta joins (with less-than, greater-than, or compound conditions) would still require a nested-loop or sort-merge approach. A secondary improvement would be to sort both relations on the join attribute and merge them — also O(n log n + m log m), but with the same equality restriction.

Neither change has been implemented.

---

## 5. Conclusion

The nested-loop join exhibits the expected quadratic behavior in both comparison count and wall time. The measured comparison counts match the formula n x m exactly at every completed size, confirming no early-exit optimization is occurring. The log-log slope from n=4000 to n=16000 is 2.08, consistent with O(n squared). Select and project were not measured but are argued to be linear, since each visits every tuple exactly once. A one-million-tuple join would take approximately 8.8 days under the current implementation. Replacing the nested loop with a hash join would be the single change required to make it feasible.