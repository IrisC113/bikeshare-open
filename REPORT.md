# Results

Working draft through Exercise 4; the Exercise 5 argument and teammate audit remain for later. All R² and MAE values below use the original daily-ride count scale. These first eight rows describe the **untransformed** pipeline before and after adding `cnt_roll_3`; the after rows match `reports/metrics.json`.

| Feature set | Model | Validation R² | Validation MAE | Test R² | Test MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| Before: 14 features | baseline_mean | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| Before: 14 features | baseline_persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| Before: 14 features | ridge | 0.6475 | 832.9 | 0.5833 | 947.1 |
| Before: 14 features | hgb | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| After: 15 features | baseline_mean | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| After: 15 features | baseline_persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| After: 15 features | ridge | 0.6439 | 836.5 | 0.5800 | 946.2 |
| After: 15 features | hgb | 0.1983 | 1311.6 | -0.5338 | 1998.7 |

`cnt_roll_3` uses only the three preceding calendar days. Its validation delta was −0.0036 R² and +3.6 MAE for Ridge, and −0.0202 R² and +15.0 MAE for HGB. It is retained to demonstrate the required feature/test workflow, despite not supporting a deployment improvement. The temporal split and all sample counts stayed fixed: 348 training, 182 validation and 184 test rows. Exercise 4 keeps this same 15-feature matrix for every comparison.

# Headline finding

The identity `casual + registered == cnt` makes the starter's perfect-score leakage demonstration invalid as forecasting; both components are excluded from actual model inputs. Under the temporal split, predicting the training mean gives test R² −2.1441, original-target Ridge reaches 0.5800, and original-target HGB reaches −0.5338. Demand-level growth makes this a difficult transfer problem for the fitted tree model. Yesterday's count already reaches 0.5099 and has lower MAE than Ridge (840.1 versus 946.2), so Ridge's positive R² is not sufficient evidence of deployment value. The added three-day feature slightly worsened validation performance. The separate target-normalization experiment below makes HGB competitive, while preserving the canonical results above.

# Exercise 4: target transformation

**Design and availability.** Let `m_t = mean(y_(t-1), ..., y_(t-7))`, the existing, calendar-verified `cnt_roll_7` feature. Before fitting candidates, the local plan specified exactly two target representations:

- Additive residual: `z_t = y_t - m_t`, with inverse prediction `y_hat_t = m_t + z_hat_t`.
- Log ratio: `z_t = log(1 + y_t) - log(1 + m_t)`, with inverse prediction `y_hat_t = exp(log(1 + m_t) + z_hat_t) - 1`.

Only training labels are transformed. The transformed label is never appended to the predictor frame. Inversion receives predicted residuals and the known historical reference, not today's true count. The `+1` handles zero counts. Predictions are not clipped and no inverse-log bias correction is fitted. This is a rolling, one-day-ahead forecasting interpretation: the preceding seven observed counts must be available at each prediction date. A batch forecast of an entire future half-year without those daily observations would require another procedure. The starter's other input-availability assumptions are shared across comparisons.

**Validation selection.** All candidates retain the same features, 2011 training rows and fixed model settings: Ridge `alpha=1`, HGB `max_iter=300, random_state=0`. Neither model is refitted on validation data. Both transformations are also evaluated with Ridge, and predicting `m_t` directly is an additional baseline. MAE and R² are calculated **after inversion**, so improved scores are not an artifact of evaluating errors on a logarithmic scale. Validation runs exclude H2 2012 rows with a Parquet predicate.

| Model | Validation R² | Validation MAE |
| --- | ---: | ---: |
| Training-mean baseline | -0.9318 | 2002.2 |
| Yesterday baseline | 0.4507 | 900.6 |
| Prior-seven-day mean baseline | 0.5945 | 823.9 |
| Ridge, original target | 0.6439 | 836.5 |
| HGB, original target | 0.1983 | 1311.6 |
| Ridge, additive residual | 0.6545 | 822.0 |
| HGB, additive residual | 0.7209 | 722.4 |
| Ridge, log ratio | 0.5144 | 972.4 |
| HGB, log ratio | 0.7488 | 687.6 |

The predeclared rule selected the greatest HGB validation R², with MAE as tie-breaker: the log ratio won at 0.7488/687.6. Before accessing transformed test scores, I also locked the strongest already-evaluated linear control, additive-residual Ridge at 0.6545/822.0. This strengthens the final comparison beyond original Ridge at 0.6439/836.5. The choices, source/data hashes and one output destination were frozen in the local selection manifest before held-out evaluation.

**Held-out protocol.** Earlier exercises and the self-audit had already reported/reproduced the original pipeline's test metrics; I do not claim this test set was globally unseen. Within Exercise 4, no transformed test score informed the choice. After freezing, one new comparison batch evaluated the selected HGB representation and fixed controls on all 184 H2 2012 rows. No alternative HGB representation was tested or substituted after seeing these results. Existing regression tests also check the unchanged original Ridge baseline; they do not select a target transformation.

| Frozen comparison | Test R² | Test MAE |
| --- | ---: | ---: |
| Training-mean baseline | -2.1441 | 2847.7 |
| Yesterday baseline | 0.5099 | 840.1 |
| Prior-seven-day mean baseline | 0.4796 | 871.6 |
| Ridge, original target | 0.5800 | 946.2 |
| HGB, original target | -0.5338 | 1998.7 |
| Ridge, log ratio (same-transform control) | 0.1948 | 1360.7 |
| Ridge, additive residual (best linear control) | 0.5890 | 932.8 |
| HGB, log ratio (selected) | 0.6166 | 847.5 |

**Interpretation.** The selected HGB beats original HGB and the strongest validation-selected linear control on held-out R² (0.6166 versus 0.5890) and MAE (847.5 versus 932.8). Its validation advantage narrows substantially on test. Yesterday's baseline still has slightly lower test MAE, 840.1 versus 847.5: a 7.4-ride disadvantage for the transformed tree. This is evidence of competitiveness, not an unconditional deployment win.

The transformation is defensible as a **hybrid rolling-level forecast with a nonlinear relative correction**. It supplies an explicit rule for transferring a recently observed demand level; it does not establish that an unmodified tree learned to extrapolate the growth trend. In this fitted comparison, original HGB's maximum test prediction is 5625.3, below the 2011 training maximum of 6043; transformed HGB predicts above that old maximum on 79 days and reaches 9497.0. The count-scale metrics and the extra rolling-mean/Ridge controls show that the improvement is more than a rescaling trick. The assumptions remain substantive: relative deviations must transfer over time, the seven-day level can lag abrupt changes, and inverse-log predictions are not explicitly corrected for mean bias. A single validation half-year and one final test half-year support a limited finding, not a general superiority claim. I retain the method as an experimental flag and leave the default target and canonical metrics unchanged.

**Reproduction.** From the repository root, reproduce validation with:

```sh
python -m src.train --target-transform residual --validation-only --out reports/exercise4/residual_validation.json
python -m src.train --target-transform log_ratio --validation-only --out reports/exercise4/log_ratio_validation.json
```

For a fresh checkout, after reproducing validation, create a frozen manifest before inspecting test:

```python
import json
from pathlib import Path
from src.train import experiment_fingerprints
lock = {"selected_transform": "log_ratio", "ridge_control": "residual",
        "fingerprints": experiment_fingerprints(),
        "test_output": str(Path("reports/exercise4/final_evaluation.json").resolve())}
Path("reports/exercise4/selection.json").write_text(json.dumps(lock), encoding="utf-8")
```

```sh
python -m src.train --target-transform log_ratio --ridge-control residual --include-test --selection reports/exercise4/selection.json --out reports/exercise4/final_evaluation.json
```

The test command rejects code/data drift, a different locked comparison, the canonical metrics destination, or an already-existing frozen output. The original local manifest also retains validation-artifact hashes and its freeze time. `make all` continues to run the original untransformed pipeline. Detailed plans, transcripts, metrics and logs under `reports/exercise4/` are local/ignored; the required experimental method and results are included here and the implementation is in `src/train.py` behind flags.

# Exercise 5: ridge vs persistence

Pending the separate Exercise 5 deployment argument for the original Ridge/persistence comparison. The Exercise 4 result does not by itself settle that question.

# Attribution

Local model: **qwen3.5:4b** (4.2B, Q4_K_M), served by Ollama as `bikeshare-coder` with a 65,536-token context. No local model-size switch was made during Exercise 4. Claude Code is the harness; these local runs did not use an Anthropic-hosted Claude model.

Agent-generated or integrated work:

- Existing local-Claude records cover the `cnt_roll_3` implementation/test, controlled fault/repair experiments and the genuine SDK self-audit output.
- For Exercise 4, local Claude Code generated and applied the two target-transform/inverse functions through an actual Edit call; its post-edit leakage hook passed. I reviewed the result and added the missing nonnegative-domain and vector-shape checks.

Decisions and author review:

- The dataset, target, forbidden columns and split were prescribed by the starter. They are maintained here, not presented as newly invented research choices.
- The existing Exercise 1 record documents I review/correction of the independent named-date feature test and the decision to retain an unhelpful feature for the assignment demonstration.
- I proposed the Exercise 4 transformations, finite candidate plan, validation selection rule and interpretation under the instruction to complete this exercise. These decisions are recorded in `docs/DECISIONS.md`.

The saved self-audit predates Exercise 4's optional flags. Its original-pipeline conclusions are consistent with the preserved default code and metrics; a final audit refresh should use the finished repository after the remaining work. 