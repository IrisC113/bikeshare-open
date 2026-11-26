# Results

All scores use the original daily-ride count scale; MAE is rides/day. The eight rows compare the untransformed pipeline before and after adding `cnt_roll_3`. After-feature values match `reports/metrics.json`.

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

The split is 2011 training (348 rows), H1 2012 validation (182), and H2 2012 test (184). `cnt_roll_3` averages the three preceding calendar days, excluding today. Validation R² fell by 0.0036 for Ridge and 0.0202 for HGB; MAE rose by 3.6 and 15.0. I retain the feature to demonstrate the required feature/test workflow, while recommending against deployment on this evidence.

# Headline finding

The leaky demonstration achieves R² 1.000 because `casual + registered == cnt`; it learns addition rather than forecasting. Excluding those components and respecting time order gives test R² −2.1441 for the training mean, 0.5800 for Ridge, and −0.5338 for HGB. HGB still beats the mean baseline, despite its negative R². Demand growth challenges the tree's ability to transfer beyond the training range. Persistence already reaches R² 0.5099 and beats Ridge on MAE (840.1 versus 946.2), so positive R² alone does not justify deployment. The new feature slightly worsens validation results and is retained only for the assignment demonstration.

# Exercise 4: target transformation

**Design.** With the existing historical reference `m_t = mean(y_(t-1), ..., y_(t-7))`, compare two training targets:

- Additive residual: `z_t = y_t - m_t`; invert as `y_hat_t = m_t + z_hat_t`.
- Log ratio: `z_t = log(1 + y_t) - log(1 + m_t)`; invert as `y_hat_t = exp(log(1 + m_t) + z_hat_t) - 1`.

Only training labels are transformed; they never enter the predictors. Inversion uses predicted corrections and past counts. Scores are computed after inversion, without clipping or inverse-log bias correction. This assumes rolling one-day forecasts with seven observed preceding counts and the starter's calendar/weather availability; it is not a batch forecast without daily observations.

**Selection and results.** Every comparison uses the same 15 inputs and 2011 training rows, with Ridge `alpha=1` and HGB `max_iter=300, random_state=0`; neither is refitted on validation. The original-target comparisons are in Results; the additional comparisons are:

| Model / representation | Validation R² | Validation MAE | Test R² | Test MAE |
| --- | ---: | ---: | ---: | ---: |
| Prior-seven-day mean baseline | 0.5945 | 823.9 | 0.4796 | 871.6 |
| Ridge / additive residual | 0.6545 | 822.0 | 0.5890 | 932.8 |
| HGB / additive residual | 0.7209 | 722.4 | — | — |
| Ridge / log ratio | 0.5144 | 972.4 | 0.1948 | 1360.7 |
| HGB / log ratio (selected) | 0.7488 | 687.6 | 0.6166 | 847.5 |

The predeclared rule maximized HGB validation R², breaking ties by MAE, and selected the log ratio. The strongest validation-tested linear control, residual Ridge, was also fixed before evaluation. The choices, source/data hashes and output destination were frozen in a selection manifest. Validation runs excluded H2 2012 rows. One subsequent comparison batch evaluated the frozen models on all 184 test days; the unselected residual HGB was not tested (—). Earlier exercises had already exposed original-pipeline test scores, so the test set was not globally unseen; no transformed test score informed this selection.

**Interpretation.** Selected HGB beats residual Ridge on test R² (0.6166 versus 0.5890) and MAE (847.5 versus 932.8), but persistence retains a 7.4-ride MAE advantage. The method is defensible as a rolling demand level plus a nonlinear relative correction, with useful count-scale improvements over the rolling mean and linear controls. It does not show that an unmodified tree learned trend extrapolation: original HGB peaks at 5625.3, below the training maximum of 6043; normalized HGB reaches 9497.0 and exceeds that old maximum on 79 test days. Relative deviations must transfer over time, the seven-day level may lag changes, and inverse-log bias remains uncorrected. The validation advantage narrows on test; this is evidence of competitiveness on one split, rather than general superiority.

**Reproduction.** `make all` reproduces the untransformed canonical metrics. The transformation remains behind `--target-transform`; fresh-checkout validation and frozen-test commands are in [README.md](README.md#target-transformation-experiment-exercise-4). Local experiment artifacts remain ignored.

# Exercise 5: ridge vs persistence

For daily operations with costs proportional to absolute forecast error, I would retain “yesterday again” rather than deploy the current untransformed Ridge. On the same 184 test days, Ridge raises R² from 0.5099 to 0.5800 (+0.0701, approximately 14.3% lower MSE), but increases MAE from 840.1 to 946.2 rides/day: 106.1 more, or 12.6% worse. Both beat the training mean (R² −2.1441, MAE 2847.7), which does not establish Ridge's value over persistence. Lower MSE could matter if large misses carry disproportionately high costs; that would require an explicit cost-weighted evaluation. Ridge also requires calendar/weather inputs, lag construction, scaling and fitted coefficients, while persistence needs only the latest count. Without a gain under the stated absolute-error objective, I would keep the simpler baseline. This judgment concerns canonical Ridge; Exercise 4's normalized HGB is a separate experiment.

# Attribution

Local model: **qwen3.5:4b** (4.2B, Q4_K_M), served by Ollama as `bikeshare-coder` with a 65,536-token context. Exercise 4 used the same local model throughout. Claude Code provided the harness; the local runs did not use an Anthropic-hosted Claude model. The dataset, target, forbidden columns and temporal split came from the starter.

**Agent-generated or integrated work:**

- Codex assisted with drafting and revising `REPORT.md`, checking reported values against saved metrics, consolidating tables, and improving wording and structure.
- The `cnt_roll_3` implementation and test, controlled fault/repair experiments, and SDK self-audit output are supported by the local-Claude run records.
- In Exercise 4, local Claude Code applied the target-transform and inverse functions through an actual Edit call; the post-edit leakage hook passed.
- The `/seed-fault` skill and isolated-copy helper package the repeated Exercise 2 workflow. All three faults triggered a named test failure and manual hook exit 2, then passed after restoration. These checks are separate from the local-Claude hook events.

**Author decisions and review**, recorded in `docs/DECISIONS.md`:

- I reviewed and corrected the independent named-date feature test and retained the unhelpful feature for the assignment demonstration.
- I proposed the Exercise 4 transformations, finite candidate plan, validation selection rule and interpretation. I reviewed the generated functions and added the missing nonnegative-domain and vector-shape checks.
- For Exercise 5, I drafted the conditional deployment argument and calculated the differences from the existing canonical scores.

The final SDK self-audit covered the current pipeline and target-transform code. It reported no leakage and passed the temporal, baseline and reproducibility checks, with high confidence. The structured result is saved in `reports/audit.jsonl`.
