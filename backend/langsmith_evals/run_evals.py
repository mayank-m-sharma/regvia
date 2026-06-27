"""LangSmith evaluation runner for the RegVia RAG pipeline.

Usage:
    LANGCHAIN_API_KEY=<key> LANGCHAIN_TRACING_V2=true \\
    LANGCHAIN_PROJECT=regvia-copilot \\
    uv run python langsmith_evals/run_evals.py --document-id <uuid>

Requirements:
  - A document must already be uploaded and processed (status=ready).
  - LANGCHAIN_API_KEY must be set.
  - Backend must be reachable at REGVIA_API_URL (default: http://localhost:8000).

The script uploads the golden_dataset.json to LangSmith as dataset
'regvia-rag-evals', runs each question through /api/v1/chat, and
evaluates the answer using an LLM-as-judge (gpt-4o-mini).
Pass threshold is 80% (4 of 5 examples rated correct).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx
from langsmith import Client
from langsmith.evaluation import LangChainStringEvaluator, evaluate

_DATASET_NAME = "regvia-rag-evals"
_GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"
_API_URL = os.getenv("REGVIA_API_URL", "http://localhost:8000")
_PASS_THRESHOLD = 0.80


def _load_or_create_dataset(client: Client) -> str:
    """Return dataset ID, creating it from golden_dataset.json if absent."""
    datasets = list(client.list_datasets(dataset_name=_DATASET_NAME))
    if datasets:
        dataset_id = str(datasets[0].id)
        print(f"Using existing dataset '{_DATASET_NAME}' ({dataset_id})")
        return dataset_id

    golden = json.loads(_GOLDEN_PATH.read_text())
    dataset = client.create_dataset(_DATASET_NAME)
    client.create_examples(
        inputs=[{"question": ex["question"]} for ex in golden],
        outputs=[{"answer": ex["expected_answer"]} for ex in golden],
        dataset_id=dataset.id,
    )
    print(f"Created dataset '{_DATASET_NAME}' with {len(golden)} examples")
    return str(dataset.id)


def _make_predict(
    document_id: str,
) -> Callable[[dict[str, str]], dict[str, str]]:
    """Return a predict function that calls /api/v1/chat for a given document."""

    def predict(inputs: dict[str, str]) -> dict[str, str]:
        resp = httpx.post(
            f"{_API_URL}/api/v1/chat",
            json={"question": inputs["question"], "document_id": document_id},
            timeout=60,
        )
        resp.raise_for_status()
        return {"answer": resp.json()["data"]["answer"]}

    return predict


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RegVia RAG evals via LangSmith")
    parser.add_argument("--document-id", required=True, help="UUID of a ready document")
    args = parser.parse_args()

    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("ERROR: LANGCHAIN_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    client = Client(api_key=api_key)
    dataset_id = _load_or_create_dataset(client)

    evaluator = LangChainStringEvaluator(
        "qa",
        config={"llm": None},  # uses default LLM (requires OPENAI_API_KEY)
        prepare_data=lambda run, example: {
            "prediction": run.outputs["answer"] if run.outputs else "",
            "reference": example.outputs["answer"] if example.outputs else "",
            "input": example.inputs["question"],
        },
    )

    results = evaluate(
        _make_predict(args.document_id),
        data=dataset_id,
        evaluators=[evaluator],
        experiment_prefix="regvia-rag",
    )

    scores = [
        row.get("score", 0)
        for r in results
        for row in [cast(Any, r).get("feedback", {})]
        if isinstance(row, dict)
    ]
    pass_rate = sum(scores) / len(scores) if scores else 0.0
    print(f"\nEval results: {pass_rate:.0%} pass rate ({sum(scores)}/{len(scores)})")

    if pass_rate < _PASS_THRESHOLD:
        print(f"FAILED: below {_PASS_THRESHOLD:.0%} threshold", file=sys.stderr)
        sys.exit(1)
    print("PASSED")


if __name__ == "__main__":
    main()
