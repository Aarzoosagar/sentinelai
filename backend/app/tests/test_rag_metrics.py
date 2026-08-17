from app.services.rag.evaluation import EvaluationCase, aggregate_metrics, first_relevant_rank, metrics_for_query


def test_first_relevant_rank_and_empty_retrieval():
    assert first_relevant_rank(["a", "b", "c"], ["a"]) == 1
    assert first_relevant_rank(["a", "b", "c"], ["c"]) == 3
    assert first_relevant_rank([], ["a"]) is None


def test_metrics_are_set_aware_and_handle_large_k():
    assert metrics_for_query(["a", "b"], ["a", "c"], 5) == {"hit": True, "recall": 0.5}
    assert metrics_for_query([], ["a"], 3) == {"hit": False, "recall": 0.0}


def test_aggregate_metrics_includes_mrr_and_multiple_relevant_ids():
    records = [
        {"first_relevant_rank": 1, "hit_at_1": True, "recall_at_1": 0.5, "hit_at_3": True, "recall_at_3": 1.0, "hit_at_5": True, "recall_at_5": 1.0},
        {"first_relevant_rank": None, "hit_at_1": False, "recall_at_1": 0.0, "hit_at_3": False, "recall_at_3": 0.0, "hit_at_5": False, "recall_at_5": 0.0},
    ]
    metrics = aggregate_metrics(records)
    assert metrics["hit_at_1"] == 0.5
    assert metrics["recall_at_3"] == 0.5
    assert metrics["mrr"] == 0.5
