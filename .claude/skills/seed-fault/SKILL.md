---
name: seed-fault
description: Recheck the bikeshare verification loop by seeding a known leakage, rolling-window, or encoder fault in an isolated copy, recording failure evidence, and restoring it.
allowed-tools: Read, Bash(python .claude/skills/seed-fault/scripts/seed_fault.py *)
---

# Seed, record, restore: $ARGUMENTS

Package the controlled fault workflow repeated in Exercise 2. Keep the
starter's `/new-feature` skill and the original Exercise 2 evidence intact.

1. Interpret `$ARGUMENTS` as exactly one supported fault name:
   - `forbidden-column`: admit `casual` to `feature_columns`.
   - `rolling-today`: remove `.shift(1)` from `cnt_roll_7`.
   - `unknown-weather`: disable the encoder's unknown-label exception.
   Reject other arguments; do not interpolate free-form text into a shell.
2. From the repository root, run the packaged helper with that literal name:
   `python .claude/skills/seed-fault/scripts/seed_fault.py unknown-weather`
   Replace only the final name with the requested supported value. It uses
   the current Python environment and Git Bash on Windows (`--bash PATH`
   can select a different installed Bash). Dependencies must already be installed.
3. Inspect the helper's `result.json` and complete stdout/stderr logs under
   the printed `reports/seed_fault/` directory. Success requires a green
   baseline, the named test failing with pytest exit 1, hook exit 2 with
   that same failure, byte-for-byte restoration, green restored tests and
   hook exit 0. A timeout or unrelated failure is not successful detection.
4. Report the exact mutation, failing test, observed exit codes and evidence
   directory. Say explicitly that the helper feeds a PostToolUse payload to
   the hook **manually**; it does not prove a Claude Code Edit triggered the
   hook and has no agent repair-turn count. Never substitute these records
   for Exercise 2's genuine Claude Code event transcripts.

The helper changes only a retained temporary copy under ignored `reports/`;
it restores that copy's source in `finally`, including on failure. It checks
that original inputs and canonical metrics retain their hashes. It does not
fit models, access the network, modify the working source/raw data, commit,
or upload. Leave existing user edits untouched. If verification fails,
report the saved evidence rather than weakening a test or permission rule.
