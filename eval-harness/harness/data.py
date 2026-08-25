"""
Dataset loading with leakage-safe splitting.

Data contract (three files in one directory):

  resumes.jsonl   {"resume_id": str, "candidate_id": str, "category": str, "text": str}
  jobs.jsonl      {"job_id": str, "category": str, "title": str, "text": str}
  qrels.csv       job_id,resume_id,relevance        (relevance: 0-3 graded)

'qrels' is the standard IR term for relevance judgements. Graded relevance:
  3 = strong match, 2 = partial, 1 = weak, 0 = irrelevant
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


@dataclass
class Resume:
    resume_id: str
    candidate_id: str
    category: str
    text: str
    sections: dict[str, str] = field(default_factory=dict)


@dataclass
class Job:
    job_id: str
    category: str
    title: str
    text: str


@dataclass
class Dataset:
    resumes: list[Resume]
    jobs: list[Job]
    qrels: dict[tuple[str, str], float]      # (job_id, resume_id) -> relevance
    label_source: str = "unknown"

    def relevance(self, job_id: str, resume_id: str) -> float:
        """Unjudged pairs are treated as irrelevant (standard IR convention)."""
        return self.qrels.get((job_id, resume_id), 0.0)

    def __repr__(self) -> str:
        return (
            f"Dataset(resumes={len(self.resumes)}, jobs={len(self.jobs)}, "
            f"judgements={len(self.qrels)}, labels='{self.label_source}')"
        )


# ----------------------------------------------------------------------
def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path.name} line {lineno}: invalid JSON — {e}") from e
    return rows


def load_dataset(data_dir: str | Path, label_source: str = "unknown") -> Dataset:
    """Load and validate a dataset directory. Fails loudly on malformed input."""
    d = Path(data_dir)
    for required in ("resumes.jsonl", "jobs.jsonl", "qrels.csv"):
        if not (d / required).exists():
            raise FileNotFoundError(f"Missing {required} in {d}")

    resumes = [
        Resume(
            resume_id=str(r["resume_id"]),
            candidate_id=str(r.get("candidate_id", r["resume_id"])),
            category=str(r.get("category", "")),
            text=str(r["text"]),
            sections=r.get("sections", {}) or {},
        )
        for r in _read_jsonl(d / "resumes.jsonl")
    ]
    jobs = [
        Job(
            job_id=str(j["job_id"]),
            category=str(j.get("category", "")),
            title=str(j.get("title", "")),
            text=str(j["text"]),
        )
        for j in _read_jsonl(d / "jobs.jsonl")
    ]

    qdf = pd.read_csv(d / "qrels.csv", dtype={"job_id": str, "resume_id": str})
    missing_cols = {"job_id", "resume_id", "relevance"} - set(qdf.columns)
    if missing_cols:
        raise ValueError(f"qrels.csv missing columns: {missing_cols}")

    # Referential integrity — catches typos that would silently score as 0
    resume_ids = {r.resume_id for r in resumes}
    job_ids = {j.job_id for j in jobs}
    unknown_r = set(qdf["resume_id"]) - resume_ids
    unknown_j = set(qdf["job_id"]) - job_ids
    if unknown_r:
        raise ValueError(f"qrels references unknown resume_ids: {sorted(unknown_r)[:5]}")
    if unknown_j:
        raise ValueError(f"qrels references unknown job_ids: {sorted(unknown_j)[:5]}")

    qrels = {
        (str(row.job_id), str(row.resume_id)): float(row.relevance)
        for row in qdf.itertuples()
    }
    return Dataset(resumes=resumes, jobs=jobs, qrels=qrels, label_source=label_source)


# ----------------------------------------------------------------------
def split_by_candidate(
    dataset: Dataset, test_size: float = 0.2, seed: int = 42
) -> tuple[Dataset, Dataset]:
    """Split resumes by CANDIDATE, never by row.

    THIS IS THE CRITICAL ANTI-LEAKAGE STEP. If one candidate has two resumes
    and they land on opposite sides of the split, the model has effectively
    seen the test data. Splitting by row is the single most common way
    student ML projects report inflated numbers.
    """
    ids = [r.resume_id for r in dataset.resumes]
    groups = [r.candidate_id for r in dataset.resumes]

    n_groups = len(set(groups))
    if n_groups < 2:
        raise ValueError("Need at least 2 distinct candidates to split")

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(ids, groups=groups))

    def _subset(indices) -> Dataset:
        subset_resumes = [dataset.resumes[i] for i in indices]
        keep = {r.resume_id for r in subset_resumes}
        return Dataset(
            resumes=subset_resumes,
            jobs=dataset.jobs,                       # jobs are queries, shared
            qrels={k: v for k, v in dataset.qrels.items() if k[1] in keep},
            label_source=dataset.label_source,
        )

    train, test = _subset(train_idx), _subset(test_idx)

    # Assert the invariant rather than trusting it
    overlap = {r.candidate_id for r in train.resumes} & {r.candidate_id for r in test.resumes}
    assert not overlap, f"Candidate leakage detected: {overlap}"

    return train, test
