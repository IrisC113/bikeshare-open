# Seeded Faults

## Exercise 1: Failing Feature Test

### Feature and availability

Feature: `cnt_roll_3`, the mean daily ridership over the previous three calendar days, excluding the prediction date.

At prediction time for date d, all inputs are known because the feature uses only counts from d-1, d-2, and d-3. No input comes from the prediction date or a future date.

### Named-date manual calculation

Test: `tests/test_leakage.py::test_cnt_roll_3_excludes_today`.
Prediction date: `2011-06-15`.

| Historical date | Raw `cnt` |
| --- | ---: |
| 2011-06-12 | 4460 |
| 2011-06-13 | 5020 |
| 2011-06-14 | 4891 |

Expected mean: `(4460 + 5020 + 4891) / 3 = 4790.333333333333`.
The test independently selects these dates from `load_raw()` and computes their mean without using a generated rolling feature.

### Human intervention

I reviewed Claude's initial expected-value calculation, `expected = sum(feats[TARGET] for d in window) / 3`, and identified that it reused the entire processed target Series instead of selecting the three historical raw counts. I directed Claude to correct the test to use:

```python
raw_counts = load_raw().set_index("dteday")[TARGET]
expected = sum(raw_counts.loc[d] for d in window) / 3
```

I reviewed and approved the corrected test before recording this evidence. Existing tests were not modified.

### Execution and failure reason

Command: `python -m pytest -q`.
Exit code: `1`.
Actual result: `1 failed, 14 passed in 6.35s`.

The new test fails when accessing the absent `cnt_roll_3` column, raising `AttributeError`. The feature has not been implemented, and all 14 original tests pass. This is the intended red state before implementation.

The output below was copied directly from the original captured pytest stdout, extracted from Bash tool-result event `call_961m88r4` in `reports/exercise1_red_claude.jsonl`. Only the tool's `Exit code 1` wrapper was excluded from stdout and recorded separately above. The capture is also retained locally as `reports/exercise1_red_pytest_output.txt`. No output was fabricated, reconstructed, or replaced by a later test run.

### Actual failing pytest output

```text
.........F.....                                                          [100%]
================================== FAILURES ===================================
_______________________ test_cnt_roll_3_excludes_today ________________________

feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 28 columns]

    def test_cnt_roll_3_excludes_today(feats):
        """cnt_roll_3 must be the mean of the 3 calendar days *before* today.
    
        For 2011-06-15: previous three days are 2011-06-14, 2011-06-13, 2011-06-12.
        The feature must equal the mean of those three dates' raw counts."""
        test_date = "2011-06-15"
        window = [pd.Timestamp("2011-06-14"), pd.Timestamp("2011-06-13"), pd.Timestamp("2011-06-12")]
        raw_counts = load_raw().set_index("dteday")[TARGET]
        expected = sum(raw_counts.loc[d] for d in window) / 3
>       assert feats.set_index("dteday").cnt_roll_3[test_date] == pytest.approx(expected, rel=1e-9)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_leakage.py:69: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self =             instant  season      yr  ... cnt_lag_1 cnt_lag_7   cnt_roll_7
dteday                               ...    ... 1787.0  1530.142857
2012-12-31    731.0  WINTER  2012.0  ...    1796.0     920.0  1531.428571

[714 rows x 27 columns]
name = 'cnt_roll_3'

    @final
    def __getattr__(self, name: str):
        """
        After regular attribute access, try looking up the name
        This allows simpler access to columns for interactive use.
        """
        # Note: obj.x will always call obj.__getattribute__('x') prior to
        # calling obj.__getattr__('x').
        if (
            name not in self._internal_names_set
            and name not in self._metadata
            and name not in self._accessors
            and self._info_axis._can_hold_identifiers_and_holds_name(name)
        ):
            return self[name]
>       return object.__getattribute__(self, name)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: 'DataFrame' object has no attribute 'cnt_roll_3'. Did you mean: 'cnt_roll_7'?

C:\Users\shuji\AppData\Roaming\Python\Python314\site-packages\pandas\core\generic.py:6194: AttributeError
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_cnt_roll_3_excludes_today - AttributeError...
1 failed, 14 passed in 6.35s
```

## Exercise 2: Controlled faults and hook evidence

Experiments below use the local `bikeshare-coder` Ollama model, based on
`qwen3.5:4b` (4.2B, Q4_K_M, 65,536-token configured context), through Claude
Code. The local model's actual Edit/Bash calls and hook lifecycle events are retained under `reports/exercise2/`. These are controlled, explicitly requested mutations;
the model was told the exact fault to introduce and to repair it after hook
feedback. This measures execution and repair, not unprompted fault discovery.

Before mutation: `python -m pytest tests/ -q` returned **16 passed**; a direct
hook smoke check returned exit 0 and empty stderr. The new weather test uses
`STORM` to exercise the unknown-label branch, which the original data never
reaches. Hook portability fixes quote the project path, use `python`, and
normalize backslashes; the `Edit|Write` matcher and raw-data deny rules remain.

For repair counts, count distinct assistant response IDs after the faulting
Edit's hook feedback through the response that repairs it. Read-only
inspections before seeding and final verification are reported separately.
Full transcripts preserve the sequence so the count can be checked. The
initial first-fault invocation was stopped before any tool call or edit;
`fault1_initial_no_edit_*` preserves that attempt. The successful retry and
later runs use a shorter task-specific system prompt with the same local
model and project hook/deny settings explicitly loaded. No repair required
a follow-up user message.



### Fault 1: Forbidden `casual` admitted to the feature list

Exact mutation, made by Claude Code's Edit tool:

```diff
--- src/features.py (safe)
+++ src/features.py (deliberate fault)
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN or c == "casual"]
```

**Automatic detection.** The first Edit triggered `PostToolUse:Edit`;
hook `93c51cd9-1146-43f1-b39d-d25d8708fd75` returned exit **2**. Its feedback reached the
model before its next response. The model restored the original code in
**1 response(s)** after that feedback, without a further user prompt.
The repair Edit triggered another hook, which returned exit **0** with
empty stderr. There were 5 assistant responses in the whole
run, including reading, seeding, repairing and verification/final reporting;
Claude Code's reported `num_turns` was 5.

**Independent full red run.** After the automatic failure, while the fault
was still present, then captured `python -m pytest tests/ -q` (exit 1):

```text
.....F..........                                                         [100%]
================================== FAILURES ===================================
_________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_3   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...     134....333333  1530.142857
713 2012-12-31    731.0  WINTER  ...      920.0  2077.333333  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_3', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests\test_leakage.py:31: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 10.43s
```

**Automatic hook stderr, verbatim.** This is the hook's own test run, not
the independent full-suite run above; the hook executes only
`python -m pytest tests/test_leakage.py -q` and emits its final 20 lines:

```text
Leakage tests failed after editing D:/A_School/UCSD/DSC 180/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_3   cnt_roll_7

0   2011-01-10     10.0  WINTER  ...     134....333333  1530.142857

713 2012-12-31    731.0  WINTER  ...      920.0  2077.333333  1531.428571



[714 rows x 29 columns]



    def test_no_forbidden_features(feats):

        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by

        construction, so this cannot discover a *new* leaky column. What it

        catches is someone editing feature_columns() or FORBIDDEN -- which is

        exactly the fault the Step 7 hook demonstrates."""

        cols = set(feature_columns(feats))

>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"

E       AssertionError: forbidden columns in feature set: {'casual'}

E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_3', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})



tests\test_leakage.py:31: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...

1 failed, 8 passed in 3.61s
```

**Agent's green verification**, command `python -m pytest tests/ -q`:

```text
................                                                         [100%]

16 passed in 4.06s
```

Evidence: `reports/exercise2/fault1_claude.jsonl`,
`fault1_run.json`, `fault1_red_pytest.txt`, `fault1_hook_stderr.txt`,
and `fault1_summary.json`. The prompt is `fault1_prompt.txt`.


### Fault 2: Today's target admitted to `cnt_roll_7`

Exact mutation, made by Claude Code's Edit tool:

```diff
--- src/features.py (safe)
+++ src/features.py (deliberate fault)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
```

**Automatic detection.** The first Edit triggered `PostToolUse:Edit`;
hook `abc58150-5b3f-45a1-994d-ad0ffa73a918` returned exit **2**. Its feedback reached the
model before its next response. The model restored the original code in
**1 response(s)** after that feedback, without a further user prompt.
The repair Edit triggered another hook, which returned exit **0** with
empty stderr. There were 5 assistant responses in the whole
run, including reading, seeding, repairing and verification/final reporting;
Claude Code's reported `num_turns` was 5.

**Independent full red run.** After the automatic failure, while the fault
was still present, then captured `python -m pytest tests/ -q` (exit 1):

```text
.........F......                                                         [100%]
================================== FAILURES ===================================
______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_3   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...     134....333333  1531.428571
713 2012-12-31    731.0  WINTER  ...      920.0  2077.333333  1789.857143

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests\test_leakage.py:63: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 5.28s
```

**Automatic hook stderr, verbatim.** This is the hook's own test run, not
the independent full-suite run above; the hook executes only
`python -m pytest tests/test_leakage.py -q` and emits its final 20 lines:

```text
Leakage tests failed after editing D:/A_School/UCSD/DSC 180/bikeshare-open/src/features.py:
[714 rows x 29 columns]



    def test_rolling_mean_excludes_today(feats):

        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""

        by_date = feats.set_index("dteday")[TARGET]

        date = feats.dteday.iloc[200]

        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]

        if all(d in by_date.index for d in window):

            expected = sum(by_date[d] for d in window) / 7

>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)

E           assert np.float64(4389.0) == 4414.857142857143 � 0.00441486

E             

E             comparison failed

E             Obtained: 4389.0

E             Expected: 4414.857142857143 � 0.00441486



tests\test_leakage.py:63: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...

1 failed, 8 passed in 5.27s
```

**Agent's green verification**, command `cd "D:/A_School/UCSD/DSC 180/bikeshare-open" && python -m pytest tests/ -q`:

```text
................                                                         [100%]

16 passed in 2.96s
```

Evidence: `reports/exercise2/fault2_claude.jsonl`,
`fault2_run.json`, `fault2_red_pytest.txt`, `fault2_hook_stderr.txt`,
and `fault2_summary.json`. The prompt is `fault2_prompt.txt`.

The fault-2 hook capture contains U+FFFD where Windows encoded the pytest plus/minus sign in a legacy code page. It is preserved exactly as Claude Code received it. The independent red output above retains the sign; the hook now exports `PYTHONIOENCODING=utf-8` for subsequent runs.


### Fault 3: Unknown weather labels silently mapped to NaN

Exact mutation, made by Claude Code's Edit tool:

```diff
--- src/features.py (safe)
+++ src/features.py (deliberate fault)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+    if unknown:
+        pass
```

**Automatic detection.** The first Edit triggered `PostToolUse:Edit`;
hook `b6fbba12-6a3c-453d-a794-56f2ce14de59` returned exit **2**. Its feedback reached the
model before its next response. The model restored the original code in
**1 response(s)** after that feedback, without a further user prompt.
The repair Edit triggered another hook, which returned exit **0** with
empty stderr. There were 5 assistant responses in the whole
run, including reading, seeding, repairing and verification/final reporting;
Claude Code's reported `num_turns` was 5.

**Independent full red run.** After the automatic failure, while the fault
was still present, then captured `python -m pytest tests/ -q` (exit 1):

```text
......F.........                                                         [100%]
================================== FAILURES ===================================
_________________ test_weather_encoder_rejects_unknown_labels _________________

    def test_weather_encoder_rejects_unknown_labels():
        """An unseen label must raise before map/dropna can silently delete a day."""
>       with pytest.raises(ValueError, match="unmapped weather labels.*STORM"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests\test_leakage.py:36: Failed
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 15 passed in 5.50s
```

**Automatic hook stderr, verbatim.** This is the hook's own test run, not
the independent full-suite run above; the hook executes only
`python -m pytest tests/test_leakage.py -q` and emits its final 20 lines:

```text
Leakage tests failed after editing D:/A_School/UCSD/DSC 180/bikeshare-open/src/features.py:
..F......                                                                [100%]

================================== FAILURES ===================================

_________________ test_weather_encoder_rejects_unknown_labels _________________



    def test_weather_encoder_rejects_unknown_labels():

        """An unseen label must raise before map/dropna can silently delete a day."""

>       with pytest.raises(ValueError, match="unmapped weather labels.*STORM"):

             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE ValueError



tests\test_leakage.py:36: Failed

=========================== short test summary info ===========================

FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...

1 failed, 8 passed in 2.21s
```

**Agent's green verification**, command `python -m pytest tests/ -q 2>&1 | head -50`:

```text
................                                                         [100%]

16 passed in 4.36s
```

Evidence: `reports/exercise2/fault3_claude.jsonl`,
`fault3_run.json`, `fault3_red_pytest.txt`, `fault3_hook_stderr.txt`,
and `fault3_summary.json`. The prompt is `fault3_prompt.txt`.


### Fault 4: Bash copy outside the Edit/Write hook

**Observed difference from the tutorial.** In Claude Code 2.1.308 on this
machine, the model's Bash `cp` attempts were denied by its permission
checks. No hook lifecycle event occurred. The deny rules were kept intact;
permission denial is not evidence that the PostToolUse hook caught a write.
The CLI was stopped after the denials, before any successful mutation. The
run metadata confirms the raw bytes did not change, and the harness did not
need to restore them. The exact tool feedback follows:

Tool `call_pl3e1qsv`, command:

```bash
cp reports/exercise2/raw-fixtures/modified.csv data/raw/bike_daily.csv
```

```text
Permission to use Bash with command cp reports/exercise2/raw-fixtures/modified.csv data/raw/bike_daily.csv has been denied.
```

Tool `call_0q9g1kxe`, command:

```bash
cp "reports/exercise2/raw-fixtures/modified.csv" "data/raw/bike_daily.csv" 2>&1; echo "Exit code: $?"
```

```text
Permission to use Bash with command cp "reports/exercise2/raw-fixtures/modified.csv" "data/raw/bike_daily.csv" 2>&1; echo "Exit code: $?" has been denied.
```

Tool `call_pbff9oow`, command:

```bash
python -c "import shutil; shutil.copyfile('reports/exercise2/raw-fixtures/modified.csv', 'data/raw/bike_daily.csv')"
```

```text
Permission to use Bash has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.
```

**Separate authorized external-Bash experiment.** To test the hook's actual
boundary without weakening Claude Code permissions, I invoked Git Bash
outside Claude Code. This is explicitly an external-shell run, not a
successful Claude Bash tool call. The prepared fixture changes only `temp`
on the training date 2011-06-15, from 21.453349 to 22.453349. CSV shape,
targets, dates and processed row count remain unchanged. An independent
fixture comparison confirms exactly one changed model-input cell, with
714 processed rows in both versions (`fault4_feature_effect.json`).

The existing PostToolUse matcher is `Edit|Write`; an external shell has no
Claude tool event at all. Hook stderr is therefore absent (the retained
`fault4_hook_stderr.txt` is empty), not a passing hook result. Actual command
results from `fault4_external_bash.json`:

Command: `C:\Program Files\Git\bin\bash.exe -c cp reports/exercise2/raw-fixtures/modified.csv data/raw/bike_daily.csv`; exit **0**.
Raw SHA256 afterwards: `6ad8000b1f54ad7da2c1157e06de3468ebd71d1740a0c69b22b070732b57dadf`.

stdout:
```text
(empty)
```

stderr:
```text
(empty)
```

Command: `C:\Python314\python.exe -m src.ingest`; exit **0**.
Raw SHA256 afterwards: `6ad8000b1f54ad7da2c1157e06de3468ebd71d1740a0c69b22b070732b57dadf`.

stdout:
```text
OK ingest: 728 rows, 2011-01-03 -> 2012-12-31
```

stderr:
```text
(empty)
```

Command: `C:\Python314\python.exe -m pytest tests/test_leakage.py -q`; exit **0**.
Raw SHA256 afterwards: `6ad8000b1f54ad7da2c1157e06de3468ebd71d1740a0c69b22b070732b57dadf`.

stdout:
```text
.........                                                                [100%]
9 passed in 1.07s
```

stderr:
```text
(empty)
```

Command: `C:\Program Files\Git\bin\bash.exe -c cp reports/exercise2/raw-fixtures/original.csv data/raw/bike_daily.csv`; exit **0**.
Raw SHA256 afterwards: `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`.

stdout:
```text
(empty)
```

stderr:
```text
(empty)
```

The copy succeeded, changed the raw hash, and the old ingest path still
accepted the file; all nine leakage tests also passed. Copying the original
fixture back restored its exact bytes, with no fallback restore needed.
There is no automatic repair-turn count for this off-hook fault: restoration
was the explicit final step of the controlled external-shell script.

**What catches it, implemented and verified.** A pinned SHA256 check in
`make data`'s ingest path catches content changes even when the file already
exists; the same check in `load_raw()` protects direct feature-building
calls. A Stop hook could check the hash at session completion, or OS file
permissions could prevent the write itself. A PreToolUse hook for Bash
would protect Claude Bash calls, but cannot see an external shell. The
implemented checksum guard detects the changed bytes when the pipeline
reads them; it does not claim to prevent the copy.

`RAW_SHA256` lives in `src/config.py`. The guard does not update that hash
to accept a changed file. Two new parameterized contract cases confirm
that both the cached download path and direct load reject changed yet
parseable CSV bytes. After the guard was installed, the same Bash copy
still returned exit 0; the next `python -m src.ingest` returned exit 1:

```text
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "D:\A_School\UCSD\DSC 180\bikeshare-open\src\ingest.py", line 48, in <module>
    download(force="--force" in sys.argv)
    ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\A_School\UCSD\DSC 180\bikeshare-open\src\ingest.py", line 29, in download
    verify_raw_integrity()
    ~~~~~~~~~~~~~~~~~~~~^^
  File "D:\A_School\UCSD\DSC 180\bikeshare-open\src\ingest.py", line 21, in verify_raw_integrity
    raise ValueError(
    ...<2 lines>...
    )
ValueError: raw data checksum mismatch: expected a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc, got 6ad8000b1f54ad7da2c1157e06de3468ebd71d1740a0c69b22b070732b57dadf; restore the checked-in bike_daily.csv
```

Guard implementation diff (also `reports/exercise2/fault4_guard.diff`):

```diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 775774e..80d1990 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -17,6 +17,9 @@ rides) from calendar, weather, and lagged-demand features.
   for each. Derive feature lists from `FORBIDDEN`; never hand-type them.
 - **Never** split this data randomly. Use `src.train.temporal_split`.
   Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
+- Raw CSV bytes must match `RAW_SHA256`; ingest checks cached files too.
+  Restore the original data after a controlled fault; never update the hash to fit it.
+- Unknown weather labels must raise; retain the rejection test in the hook's suite.
 - Any new lag or rolling feature must be built on a gap-free calendar
   index (`src.features.reindex_to_calendar`) and must `.shift(1)` before
   it aggregates. Add a test for it in `tests/test_leakage.py`.
diff --git a/src/config.py b/src/config.py
index 405de6f..0610ed2 100644
--- a/src/config.py
+++ b/src/config.py
@@ -3,6 +3,8 @@ from pathlib import Path

 ROOT = Path(__file__).resolve().parents[1]
 RAW = ROOT / "data" / "raw" / "bike_daily.csv"
+# Exact checked-in mirror; protect reads even if a shell bypasses file tools.
+RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
 PROCESSED = ROOT / "data" / "processed" / "features.parquet"
 METRICS = ROOT / "reports" / "metrics.json"

diff --git a/src/ingest.py b/src/ingest.py
index 6654075..8822bb0 100644
--- a/src/ingest.py
+++ b/src/ingest.py
@@ -2,25 +2,39 @@

 Run: python -m src.ingest
 """
+import hashlib
 import sys
 import urllib.request

 import pandas as pd

-from src.config import DATA_URL, RAW
+from src.config import DATA_URL, RAW, RAW_SHA256

 EXPECTED_MIN_ROWS = 700
 REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


+def verify_raw_integrity() -> None:
+    """Reject changed bytes, including shell writes outside Edit/Write hooks."""
+    actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
+    if actual != RAW_SHA256:
+        raise ValueError(
+            f"raw data checksum mismatch: expected {RAW_SHA256}, got {actual}; "
+            "restore the checked-in bike_daily.csv"
+        )
+
+
 def download(force: bool = False) -> None:
     if RAW.exists() and not force:
+        verify_raw_integrity()
         return
     RAW.parent.mkdir(parents=True, exist_ok=True)
     urllib.request.urlretrieve(DATA_URL, RAW)
+    verify_raw_integrity()


 def load_raw() -> pd.DataFrame:
+    verify_raw_integrity()
     df = pd.read_csv(RAW, parse_dates=["dteday"])
     missing = REQUIRED_COLS - set(df.columns)
     if missing:
diff --git a/tests/test_contract.py b/tests/test_contract.py
index 4f7a1b8..3b5208f 100644
--- a/tests/test_contract.py
+++ b/tests/test_contract.py
@@ -3,6 +3,7 @@ import pandas as pd
 import pytest
 from sklearn.metrics import r2_score

+from src import ingest
 from src.config import LAG_WARMUP, TARGET
 from src.features import build_features, feature_columns, reindex_to_calendar
 from src.ingest import load_raw
@@ -25,6 +26,19 @@ def test_calendar_is_complete_before_lagging(raw):
     assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


+@pytest.mark.parametrize("entry_point", ["download", "load_raw"])
+def test_raw_entry_points_reject_changed_bytes(tmp_path, monkeypatch, entry_point):
+    """A cached, parseable CSV must not bypass integrity checks."""
+    original = ingest.RAW.read_bytes()
+    tampered = tmp_path / "bike_daily.csv"
+    tampered.write_bytes(original + b"\n")
+    # A shape/schema-only check would still accept this modified file.
+    assert pd.read_csv(tampered).shape == pd.read_csv(ingest.RAW).shape
+    monkeypatch.setattr(ingest, "RAW", tampered)
+    with pytest.raises(ValueError, match="raw data checksum mismatch"):
+        getattr(ingest, entry_point)()
+
+
 def test_only_expected_rows_are_dropped(raw, feats):
     """Rows may only vanish for the lag warm-up or downstream of a genuinely
     absent day -- never because an encoder produced a silent NaN.
```

The verification script restored `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc` in its finally block.

### Final checks and attribution

The three agent fault/repair experiments were performed before adding the
two integrity-test cases, so their full-suite logs contain 16 tests. The
final suite contains 18. Its first sandbox-only invocation could not create
pytest temporary fixtures; that environment error is preserved in
`final_tests_sandbox_temp_error.txt`. Running the same command outside the
filesystem sandbox, with pytest's normal temporary directory, produced:

```text
..................                                                       [100%]
18 passed in 4.71s
```

Final original CSV SHA256: `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`.
`CLAUDE.md` is 44 lines (limit: 60).

| Fault | Detection | Responses to repair after hook feedback |
| --- | --- | ---: |
| Forbidden `casual` feature | Automatic hook exit 2, then exit 0 | 1 |
| Unshifted seven-day mean | Automatic hook exit 2, then exit 0 | 1 |
| Removed weather exception | Automatic hook exit 2, then exit 0 | 1 |
| Raw-data Bash copy | Claude tool attempt denied; external Bash copy accepted before guard; ingest rejected it after guard | Not applicable; explicit restore |

Local Qwen3.5 4B through Claude Code performed the three Edit-based
mutations and their repairs, and attempted the Bash copy. Added the
weather test, Windows hook fixes, integrity guard and its tests; ran the
separate external-shell experiment; captured evidence and wrote this
document. The fault prompts supplied the intended mutations explicitly.
No claim is made that the local model discovered these faults unprompted.
No feature, split, estimator or committed metrics was changed by Exercise 2.

