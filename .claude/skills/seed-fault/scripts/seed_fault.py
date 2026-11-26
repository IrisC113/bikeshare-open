"""Run one controlled fault in an isolated snapshot; retain real evidence."""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


FAULTS = {
    "forbidden-column": (
        "return [c for c in numeric if c not in FORBIDDEN]",
        'return [c for c in numeric if c not in FORBIDDEN or c == "casual"]',
        "test_no_forbidden_features",
    ),
    "rolling-today": (
        'out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()',
        'out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()',
        "test_rolling_mean_excludes_today",
    ),
    "unknown-weather": (
        'raise ValueError(f"unmapped weather labels: {sorted(unknown)}")',
        "pass  # controlled fault: suppress unknown-weather rejection",
        "test_weather_encoder_rejects_unknown_labels",
    ),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fault", choices=FAULTS)
    parser.add_argument("--bash", help="Installed Bash executable (Git Bash on Windows)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    bash = args.bash or os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if not bash and os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/bin/bash.exe"
        if candidate.is_file():
            bash = str(candidate)
    bash = bash or shutil.which("bash")
    if not bash:
        parser.error("Bash is required to exercise the existing hook")

    protected = list((root / "src").glob("*.py")) + list((root / "tests").glob("*.py"))
    protected += [root / p for p in (
        "data/raw/bike_daily.csv", "reports/metrics.json", ".claude/settings.json",
        ".claude/hooks/check_leakage.sh", ".claude/skills/new-feature/SKILL.md",
    )]
    before = {str(p.relative_to(root)): digest(p) for p in protected}
    output = root / "reports/seed_fault"
    output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=args.fault + "-", dir=output))
    work = run / "repo"
    for source in protected:
        target = work / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    env = os.environ.copy()
    env.update({"CLAUDE_PROJECT_DIR": work.as_posix(), "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    # Do not let an inherited import path run the original source instead of the copy.
    env.pop("PYTHONPATH", None)
    tests = [sys.executable, "-m", "pytest", "tests/test_leakage.py", "-q", "-p", "no:cacheprovider"]
    hook = [bash, ".claude/hooks/check_leakage.sh"]
    payload = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Edit",
                          "tool_input": {"file_path": (work / "src/features.py").as_posix()}})
    result = {"fault": args.fault, "started_utc": datetime.now(timezone.utc).isoformat(),
              "driver": "Manual hook payload, not a Claude Code event",
              "repair_turns": None, "python": sys.executable, "bash": bash,
              "evidence_directory": str(run), "stages": {}}

    def stage(name, command, stdin=None):
        completed = subprocess.run(command, cwd=work, env=env, input=stdin,
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=120)
        (run / (name + ".stdout.txt")).write_text(completed.stdout, encoding="utf-8")
        (run / (name + ".stderr.txt")).write_text(completed.stderr, encoding="utf-8")
        result["stages"][name] = {"command": command, "exit_code": completed.returncode}
        return completed

    feature = work / "src/features.py"
    original = feature.read_bytes()
    try:
        assert stage("baseline_tests", tests).returncode == 0, "baseline tests failed"
        assert stage("baseline_hook", hook, payload).returncode == 0, "baseline hook failed"
        old, new, expected = FAULTS[args.fault]
        text = original.decode("utf-8")
        assert text.count(old) == 1, "mutation anchor missing or ambiguous; inspect source"
        mutated = text.replace(old, new, 1)
        feature.write_bytes(mutated.encode("utf-8"))
        (run / "mutation.diff").write_text("".join(difflib.unified_diff(
            text.splitlines(keepends=True), mutated.splitlines(keepends=True),
            fromfile="a/src/features.py", tofile="b/src/features.py")), encoding="utf-8")
        red = stage("red_tests", tests)
        assert red.returncode == 1 and f"::{expected}" in red.stdout, "expected test did not fail"
        red_hook = stage("red_hook", hook, payload)
        assert red_hook.returncode == 2 and f"::{expected}" in red_hook.stderr, "hook missed fault"
        result["expected_failing_test"] = expected
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        feature.write_bytes(original)
        result["snapshot_source_restored"] = feature.read_bytes() == original
        for name, command, stdin in [("restored_tests", tests, None), ("restored_hook", hook, payload)]:
            try:
                assert stage(name, command, stdin).returncode == 0, f"{name} failed"
            except Exception as exc:
                result.setdefault("restoration_errors", []).append(f"{type(exc).__name__}: {exc}")
        after = {str(p.relative_to(root)): digest(p) for p in protected}
        result["original_files_unchanged"] = before == after
        result["original_hashes"] = after
        result["success"] = ("error" not in result and "restoration_errors" not in result
                             and result["snapshot_source_restored"] and before == after)
        (run / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
