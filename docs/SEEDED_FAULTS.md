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

