"""
watch_transcripts.py
Automatically runs the weekly trend pipeline when a new transcript is added to
input/transcripts/.

Design:
  - Pure polling (no external dependencies, cross-platform).
  - Handles partial uploads: a file is only processed once its size AND modified
    time have stayed unchanged for one full poll interval (i.e. the upload/copy
    has finished).
  - Idempotent: processed files are recorded in a manifest
    (output/history/processed_files.json) keyed by name + size + mtime, so a file
    is not reprocessed unless it actually changes. (The weekly pipeline itself is
    also idempotent by meeting date.)
  - Each new/changed transcript triggers:  main.py --input <file> --mode weekly
    which archives the week, ingests it into history, and regenerates the weekly
    and monthly HTML reports.

Usage:
  python src/watch_transcripts.py                 # watch forever (default)
  python src/watch_transcripts.py --once          # process backlog, then exit
  python src/watch_transcripts.py --interval 10   # poll every 10s
  python src/watch_transcripts.py --mock          # pass --mock to the pipeline
  python src/watch_transcripts.py --mark-processed # baseline existing files (no run)
  python src/watch_transcripts.py --print-only     # show what WOULD run (no run)
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_WATCH_DIR = _ROOT / "input" / "transcripts"
_MANIFEST = _ROOT / "output" / "history" / "processed_files.json"
_MAIN = _ROOT / "src" / "main.py"

# Files that are not real transcripts (Office lock/temp files, etc.)
_IGNORE_PREFIXES = ("~$", ".~")
_IGNORE_SUFFIXES = (".tmp", ".crdownload", ".part")


def _log(msg: str) -> None:
    print(f"[watch {datetime.now():%H:%M:%S}] {msg}", flush=True)


def _is_transcript(p: Path) -> bool:
    if p.suffix.lower() != ".docx":
        return False
    if p.name.startswith(_IGNORE_PREFIXES):
        return False
    if p.suffix.lower() in _IGNORE_SUFFIXES:
        return False
    return True


def _signature(p: Path) -> dict:
    st = p.stat()
    return {"size": st.st_size, "mtime": round(st.st_mtime, 3)}


def load_manifest() -> dict:
    if _MANIFEST.exists():
        return json.loads(_MANIFEST.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict) -> None:
    _MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _scan() -> dict:
    """Current transcript files with their signatures."""
    if not _WATCH_DIR.exists():
        return {}
    return {p.name: _signature(p) for p in _WATCH_DIR.iterdir()
            if p.is_file() and _is_transcript(p)}


def _needs_processing(name: str, sig: dict, manifest: dict) -> bool:
    prev = manifest.get(name)
    return prev is None or prev.get("size") != sig["size"] or prev.get("mtime") != sig["mtime"]


def run_pipeline(file_path: Path, mock: bool = False) -> bool:
    """Invoke the weekly pipeline for one transcript. Returns True on success."""
    cmd = [sys.executable, str(_MAIN), "--input", str(file_path), "--mode", "weekly"]
    if mock:
        cmd.append("--mock")
    _log(f"processing: {file_path.name}")
    env = {"PYTHONIOENCODING": "utf-8"}
    import os
    full_env = {**os.environ, **env}
    result = subprocess.run(cmd, cwd=str(_ROOT), env=full_env,
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode == 0:
        for line in (result.stdout or "").splitlines():
            if any(k in line for k in ("Archive week", "history now", "Weekly report", "Monthly report")):
                _log("  " + line.strip())
        _log(f"  done: {file_path.name}")
        return True
    _log(f"  FAILED ({file_path.name}) exit {result.returncode}")
    tail = (result.stderr or result.stdout or "").strip().splitlines()[-8:]
    for line in tail:
        _log("    " + line)
    return False


def process_ready(manifest: dict, stable: dict, mock: bool, print_only: bool) -> int:
    """Process every file whose signature is new/changed and currently stable."""
    processed = 0
    for name, sig in sorted(stable.items()):
        if not _needs_processing(name, sig, manifest):
            continue
        path = _WATCH_DIR / name
        if print_only:
            _log(f"WOULD process: {name}")
            processed += 1
            continue
        if run_pipeline(path, mock=mock):
            manifest[name] = {**sig, "processed_at": datetime.now().isoformat(timespec="seconds")}
            save_manifest(manifest)
            processed += 1
    return processed


def watch(interval: int, mock: bool, run_once: bool, print_only: bool) -> None:
    manifest = load_manifest()
    _log(f"watching {_WATCH_DIR}  (interval={interval}s, mock={mock}, once={run_once})")

    prev_scan = _scan()
    # On startup, treat files that are already stable as ready immediately.
    process_ready(manifest, prev_scan, mock, print_only)
    if run_once:
        _log("done (--once).")
        return

    while True:
        time.sleep(interval)
        current = _scan()
        # A file is "stable" when its signature matches the previous poll
        # (no in-flight upload) — only then is it safe to process.
        stable = {n: s for n, s in current.items()
                  if prev_scan.get(n) == s}
        in_flight = [n for n in current if prev_scan.get(n) != current[n]]
        for n in in_flight:
            _log(f"detected (waiting for upload to finish): {n}")
        process_ready(manifest, stable, mock, print_only)
        prev_scan = current


def mark_processed() -> None:
    """Record all current transcripts as processed without running the pipeline."""
    manifest = load_manifest()
    now = datetime.now().isoformat(timespec="seconds")
    for name, sig in _scan().items():
        manifest[name] = {**sig, "processed_at": now, "baseline": True}
    save_manifest(manifest)
    _log(f"baseline recorded for {len(manifest)} file(s) -> {_MANIFEST}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-run the weekly pipeline on new transcripts")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds (default 5)")
    parser.add_argument("--once", action="store_true", help="Process current backlog then exit")
    parser.add_argument("--mock", action="store_true", help="Pass --mock to the pipeline")
    parser.add_argument("--mark-processed", action="store_true",
                        help="Record existing files as processed without running (baseline)")
    parser.add_argument("--print-only", action="store_true",
                        help="Show which files would be processed without running anything")
    args = parser.parse_args()

    if args.mark_processed:
        mark_processed()
        return

    watch(interval=args.interval, mock=args.mock, run_once=args.once, print_only=args.print_only)


if __name__ == "__main__":
    main()
