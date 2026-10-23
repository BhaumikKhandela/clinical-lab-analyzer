"""Validate benchmark integrity and source agreement, without running the app.

Requires jsonschema and pypdf. This checks data integrity, not clinical validity.
"""
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "evals/golden/v1"


def main():
    manifest = json.loads((DATA / "manifest.json").read_text())
    schema = Draft202012Validator(json.loads((DATA / "item.schema.json").read_text()))
    datasets = {}
    for name, count in manifest["counts"].items():
        items = [json.loads(line) for line in (DATA / f"{name}.jsonl").read_text().splitlines()]
        assert len(items) == count, (name, count)
        assert len({i["id"] for i in items}) == count, f"Duplicate IDs in {name}"
        for i in items:
            schema.validate(i)
            assert not ({"expected_output", "required_claims", "verdict"} & i["input"].keys()), i["id"]
        datasets[name] = items
    paths = {f["path"] for f in manifest["files"]}
    for f in manifest["files"]:
        path = (ROOT / f["path"]).resolve()
        assert path.is_relative_to(ROOT), "Fixture escaped repository"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == f["sha256"], f["path"]

    pages = 0
    for i in datasets["extraction"]:
        fixture = i["input"]["fixture_path"]
        assert fixture in paths, fixture
        expected = i["expected_output"]
        if expected["outcome"] == "rejected":
            assert not (ROOT / fixture).read_bytes().startswith(b"%PDF")
            continue
        pdf = PdfReader(ROOT / fixture)
        pages += len(pdf.pages)
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if expected["outcome"] == "unsupported_without_ocr":
            assert not text.strip(), "Scanned fixture unexpectedly has a text layer"
            assert pdf.pages[0]["/Resources"]["/XObject"], "Scanned fixture needs actual image content"
            continue
        if expected["outcome"] == "incomplete_or_rejected":
            assert text.index("Tail Assay") > 12000, "Tail row must occur beyond real extraction cutoff"
            continue
        assert expected["row_count"] == len(expected["labs"])
        # Account for repeated analyte names at different values; match a full row,
        # not unrelated occurrences of the name and number somewhere on the page.
        source_lines = Counter(" ".join(line.split()) for line in text.splitlines())
        for lab in expected["labs"]:
            line = " ".join(str(v) for v in [lab["test_name"], lab["result"], lab["unit"] or "-",
                                               lab["reference_range"] or "(not supplied)"])
            # The existing hand-authored report leaves absent ranges blank.
            if fixture.startswith("Analyzer Service/") and lab["reference_range"] is None:
                line = " ".join(str(v) for v in [lab["test_name"], lab["result"], lab["unit"]])
            assert source_lines[line] > 0, (i["id"], line)
            source_lines[line] -= 1

    evidence = {e["id"] for e in json.loads((DATA / "evidence.json").read_text())}
    for i in datasets["retrieval"]:
        candidates = set(i["input"]["candidate_evidence_ids"])
        assert candidates <= evidence
        assert set(i["expected_output"]["relevant_evidence_ids"]) <= candidates
    for i in datasets["explanations"]:
        assert set(i["input"]["evidence_ids"]) <= evidence
    policy = json.loads((DATA / "policy.json").read_text())
    for i in datasets["classification"]:
        lab = i["input"]["lab"]
        value = Decimal(lab["result"])
        bounds = policy["potassium" if lab["test_name"] == "Potassium" else "glucose"]
        lo, hi = Decimal(str(lab["min_reference"])), Decimal(str(lab["max_reference"]))
        critical = value < Decimal(str(bounds["critical_low"])) or value > Decimal(str(bounds["critical_high"]))
        label = "Critical" if critical else "Warning" if value < lo or value > hi else "Normal"
        assert label == i["expected_output"]["status"], i["id"]
    for i in datasets["normalization"]:
        expected = i["expected_output"]
        if expected["converted_value"] is not None:
            assert Decimal(i["input"]["value"]) * Decimal(expected["factor"]) == Decimal(expected["converted_value"])
    pairs = datasets["judge_calibration"]
    assert Counter(i["expected_output"]["verdict"] for i in pairs) == {"pass": 6, "fail": 6}
    assert all(i["metadata"]["split"] == "calibration" for i in pairs)
    chat = {i["id"]: i for i in datasets["chat"]}
    assert chat["session-a"]["input"]["session_key"] != chat["session-b"]["input"]["session_key"]
    assert chat["session-a"]["input"]["report"] != chat["session-b"]["input"]["report"]
    print(f"Validated {sum(manifest['counts'].values())} items in {len(datasets)} datasets; "
          f"{len(paths)} file hashes; {pages} PDF pages. Clinical labels remain unreviewed.")


if __name__ == "__main__":
    main()
