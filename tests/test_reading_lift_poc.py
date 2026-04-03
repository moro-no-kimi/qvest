from __future__ import annotations

from reading_lift_poc.pipeline import apply_librarian_actions, build_demo_bundle
from reading_lift_poc.recommender import HybridRecommender


def test_dense_history_student_gets_collaborative_recommendation() -> None:
    bundle = build_demo_bundle()
    maya = bundle.recommendations.loc[bundle.recommendations["student_id"] == "STU-003"].sort_values("rank")
    assert not maya.empty
    assert maya.iloc[0]["title"] == "Scythe"
    assert maya.iloc[0]["strategy"] in {"collaborative", "hybrid"}


def test_sparse_history_student_uses_cold_start_path() -> None:
    bundle = build_demo_bundle()
    jonah = bundle.recommendations.loc[bundle.recommendations["student_id"] == "STU-004"].sort_values("rank")
    assert not jonah.empty
    assert jonah.iloc[0]["strategy"] == "cold_start"


def test_guardrail_blocks_out_of_band_title() -> None:
    bundle = build_demo_bundle()
    blocked = bundle.blocked_recommendations.loc[bundle.blocked_recommendations["student_id"] == "STU-003"]
    assert not blocked.empty
    assert "A Good Girl's Guide to Murder" in set(blocked["title"])


def test_librarian_pin_moves_recommendation_to_top() -> None:
    bundle = build_demo_bundle()
    student_recs = bundle.recommendations.loc[bundle.recommendations["student_id"] == "STU-003"].sort_values("rank")
    second_pick = student_recs.iloc[1]
    student = bundle.students.loc[bundle.students["student_id"] == "STU-003"].iloc[0]
    actions = [
        {
            "action_type": "pin",
            "student_id": student["student_id"],
            "student_name": student["student_name"],
            "school_id": student["school_id"],
            "school_name": student["school_name"],
            "grade": student["grade"],
            "homeroom": student["homeroom"],
            "book_id": second_pick["book_id"],
            "title": second_pick["title"],
            "anchor_title": second_pick["anchor_title"],
            "timestamp": "2026-04-02 10:00:00",
        }
    ]

    updated = apply_librarian_actions(bundle.recommendations, bundle.catalog, actions)
    updated_student = updated.loc[updated["student_id"] == "STU-003"].sort_values("rank")
    assert updated_student.iloc[0]["book_id"] == second_pick["book_id"]
    assert updated_student.iloc[0]["review_state"] == "pinned"


def test_replacement_honors_guardrails() -> None:
    bundle = build_demo_bundle()
    student_recs = bundle.recommendations.loc[bundle.recommendations["student_id"] == "STU-003"].sort_values("rank")
    first_pick = student_recs.iloc[0]
    student = bundle.students.loc[bundle.students["student_id"] == "STU-003"].iloc[0]
    actions = [
        {
            "action_type": "replace",
            "student_id": student["student_id"],
            "student_name": student["student_name"],
            "school_id": student["school_id"],
            "school_name": student["school_name"],
            "grade": student["grade"],
            "homeroom": student["homeroom"],
            "book_id": first_pick["book_id"],
            "title": first_pick["title"],
            "anchor_title": first_pick["anchor_title"],
            "replacement_book_id": "BK-018",
            "timestamp": "2026-04-02 10:05:00",
        }
    ]

    try:
        apply_librarian_actions(bundle.recommendations, bundle.catalog, actions)
    except ValueError as exc:
        assert "guardrail" in str(exc).lower()
    else:
        raise AssertionError("Expected invalid replacement to raise ValueError.")


def test_replacement_deduplicates_existing_title() -> None:
    bundle = build_demo_bundle()
    student_recs = bundle.recommendations.loc[bundle.recommendations["student_id"] == "STU-003"].sort_values("rank")
    first_pick = student_recs.iloc[0]
    second_pick = student_recs.iloc[1]
    student = bundle.students.loc[bundle.students["student_id"] == "STU-003"].iloc[0]
    actions = [
        {
            "action_type": "replace",
            "student_id": student["student_id"],
            "student_name": student["student_name"],
            "school_id": student["school_id"],
            "school_name": student["school_name"],
            "grade": student["grade"],
            "homeroom": student["homeroom"],
            "book_id": first_pick["book_id"],
            "title": first_pick["title"],
            "anchor_title": first_pick["anchor_title"],
            "replacement_book_id": second_pick["book_id"],
            "timestamp": "2026-04-02 10:07:00",
        }
    ]

    updated = apply_librarian_actions(bundle.recommendations, bundle.catalog, actions)
    updated_student = updated.loc[updated["student_id"] == "STU-003"]
    assert (updated_student["book_id"] == second_pick["book_id"]).sum() == 1


def test_recommender_returns_top_five_or_fewer() -> None:
    bundle = build_demo_bundle()
    recommender = HybridRecommender(bundle.catalog, bundle.students, bundle.checkouts)
    result = recommender.recommend_for_student("STU-003")
    assert 1 <= len(result.recommendations) <= 5