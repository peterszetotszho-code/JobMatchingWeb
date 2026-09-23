"""Quick self-test: run the full pipeline on data/ samples (no server needed)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matcher  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    resume = (root / "data" / "sample_resume.txt").read_text(encoding="utf-8")
    jd = (root / "data" / "sample_jd.txt").read_text(encoding="utf-8")

    result = matcher.analyze(resume, jd)
    if "error" in result:
        print("ERROR:", result["error"])
        return 1

    print(
        f"Fit Score: {result['fit_score']}%  "
        f"(matched={result['matched']}, partial={result['partial']}, gap={result['gap']})"
    )
    for r in result["requirements"]:
        print(f"  [{r['verdict']:7s}] sim={r['score']:.3f} ({r['category']}) {r['requirement']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
