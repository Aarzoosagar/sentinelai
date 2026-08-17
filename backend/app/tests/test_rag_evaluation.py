from app.services.rag.evaluation import EvaluationCase, evaluate_rankings


def test_evaluation_output_is_deterministic_and_records_failures():
    cases = [
        EvaluationCase("public bucket", ("s3",)),
        EvaluationCase("SSH", ("ssh", "rdp")),
    ]
    rankings = {
        "FAISS": [["iam", "s3"], ["iam"]],
        "Hybrid": [["s3"], ["ssh", "rdp"]],
        "Hybrid + Reranking": [["s3"], ["ssh", "rdp"]],
    }
    first = evaluate_rankings(cases, rankings)
    second = evaluate_rankings(cases, rankings)
    assert first == second
    assert first["systems"]["FAISS"]["metrics"] == {
        "hit_at_1": 0.0, "hit_at_3": 0.5, "hit_at_5": 0.5,
        "recall_at_1": 0.0, "recall_at_3": 0.5, "recall_at_5": 0.5, "mrr": 0.25,
    }
    assert len(first["systems"]["FAISS"]["failures"]) == 1
    assert first["best_configuration"] == "Hybrid"
