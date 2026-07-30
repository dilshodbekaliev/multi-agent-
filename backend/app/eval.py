import json
import os
from datetime import datetime, timezone

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, AnswerRelevancy
answer_relevancy = AnswerRelevancy(strictness=1)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig

from app.graph import build_graph
from app.state import new_state
from app.agents.supervisor import get_llm
from app.ingestion import get_embeddings

EVAL_SET = [
    {
        "question": "How many customers have churned in the last 90 days?",
        "ground_truth": "27 customers have churned in the last 90 days.",
    },
    {
        "question": "Why do customers churn, according to our handbook?",
        "ground_truth": (
            "Customers churn due to price sensitivity (especially Basic plan customers "
            "in their first 6 months), poor onboarding, missing integrations with "
            "accounting tools, slow support response times, and for enterprise "
            "accounts, the departure of an internal champion."
        ),
    },
    {
        "question": "What is the standard deviation of these numbers: 45, 67, 23, 89?",
        "ground_truth": "The standard deviation is approximately 28.4.",
    },
]

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "eval_results.json")


def run_eval_set():
    app_graph = build_graph()
    rows = []

    for item in EVAL_SET:
        result = app_graph.invoke(new_state(item["question"]))

        contexts = list(result.get("documents", []))
        if result.get("sql_result"):
            contexts.append(result["sql_result"])
        if result.get("code_result"):
            contexts.append(result["code_result"])
        if not contexts:
            contexts = ["(no evidence gathered)"]

        rows.append({
            "question": item["question"],
            "answer": result["answer"],
            "contexts": contexts,
            "ground_truth": item["ground_truth"],
        })

        print(f"Ran: {item['question']}")
        print(f"  -> {result['answer'][:100]}...\n")

    return rows


def save_results(df):
    records = []
    for _, row in df.iterrows():
        record = {
            "question": row.get("user_input", row.get("question", "")),
            "answer": row.get("response", row.get("answer", "")),
            "faithfulness": None if pd_isna(row.get("faithfulness")) else round(float(row.get("faithfulness")), 3),
            "answer_relevancy": None if pd_isna(row.get("answer_relevancy")) else round(float(row.get("answer_relevancy")), 3),
        }
        records.append(record)

    faith_scores = [r["faithfulness"] for r in records if r["faithfulness"] is not None]
    rel_scores = [r["answer_relevancy"] for r in records if r["answer_relevancy"] is not None]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": records,
        "averages": {
            "faithfulness": round(sum(faith_scores) / len(faith_scores), 3) if faith_scores else None,
            "answer_relevancy": round(sum(rel_scores) / len(rel_scores), 3) if rel_scores else None,
        },
    }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved results to {RESULTS_PATH}")
    return output


def pd_isna(val):
    try:
        import math
        return val is None or (isinstance(val, float) and math.isnan(val))
    except Exception:
        return val is None


def main():
    rows = run_eval_set()
    dataset = Dataset.from_list(rows)

    ragas_llm = LangchainLLMWrapper(get_llm())
    ragas_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

    run_config = RunConfig(max_workers=1, timeout=180)

    print("Scoring with RAGAS (faithfulness, answer_relevancy) — running sequentially to respect rate limits, this will take a few minutes...\n")
    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        run_config=run_config,
    )

    df = scores.to_pandas()
    print("Columns returned by this ragas version:", list(df.columns))
    print()
    print(df.to_string(index=False))

    output = save_results(df)
    print(f"\nAverage faithfulness:      {output['averages']['faithfulness']}")
    print(f"Average answer_relevancy:  {output['averages']['answer_relevancy']}")


if __name__ == "__main__":
    main()
