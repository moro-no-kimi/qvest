from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data import DemoData, create_demo_data
from .explanations import ExplanationGenerator
from .recommender import HybridRecommender


@dataclass(frozen=True)
class DemoBundle:
    schools: pd.DataFrame
    students: pd.DataFrame
    catalog: pd.DataFrame
    checkouts: pd.DataFrame
    recommendations: pd.DataFrame
    blocked_recommendations: pd.DataFrame
    school_metrics: pd.DataFrame
    weekly_metrics: pd.DataFrame
    debug_log: pd.DataFrame


def build_demo_bundle() -> DemoBundle:
    data = create_demo_data()
    recommender = HybridRecommender(data.catalog, data.students, data.checkouts)
    explainer = ExplanationGenerator()
    recommendation_rows: list[pd.DataFrame] = []
    blocked_rows: list[pd.DataFrame] = []

    for student_id in data.students["student_id"]:
        result = recommender.recommend_for_student(student_id)
        student = data.students.loc[data.students["student_id"] == student_id].iloc[0].to_dict()
        if not result.recommendations.empty:
            recs = result.recommendations.copy()
            recs["explanation"] = recs.apply(lambda row: explainer.render(row.to_dict(), student), axis=1)
            recommendation_rows.append(recs)
        if not result.blocked.empty:
            blocked_rows.append(result.blocked.copy())

    recommendations = pd.concat(recommendation_rows, ignore_index=True)
    blocked = pd.concat(blocked_rows, ignore_index=True) if blocked_rows else pd.DataFrame()

    recommendations = recommendations.merge(
        data.students[["student_id", "student_name", "school_id", "school_name", "grade", "homeroom"]],
        on="student_id",
        how="left",
    )
    debug_log = _build_debug_log(recommendations, blocked)
    school_metrics = _build_school_metrics(data, recommendations)
    weekly_metrics = _build_weekly_metrics(school_metrics)

    return DemoBundle(
        schools=data.schools,
        students=data.students,
        catalog=data.catalog,
        checkouts=data.checkouts,
        recommendations=recommendations,
        blocked_recommendations=blocked,
        school_metrics=school_metrics,
        weekly_metrics=weekly_metrics,
        debug_log=debug_log,
    )


def apply_librarian_actions(
    recommendations: pd.DataFrame,
    catalog: pd.DataFrame,
    actions: list[dict],
) -> pd.DataFrame:
    if recommendations.empty:
        return recommendations.copy()

    working = recommendations.copy()
    for action in actions:
        action_type = action["action_type"]
        student_id = action["student_id"]
        book_id = action.get("book_id")

        if action_type == "approve":
            working.loc[
                (working["student_id"] == student_id) & (working["book_id"] == book_id),
                ["review_state", "librarian_action"],
            ] = ["approved", "approved"]
        elif action_type == "pin":
            mask = (working["student_id"] == student_id) & (working["book_id"] == book_id)
            working.loc[mask, ["review_state", "librarian_action"]] = ["pinned", "pinned"]
            working.loc[mask, "rank"] = 0
        elif action_type == "suppress":
            working = working.loc[~((working["student_id"] == student_id) & (working["book_id"] == book_id))].copy()
        elif action_type == "replace":
            replacement_id = action["replacement_book_id"]
            replacement_book = catalog.loc[catalog["book_id"] == replacement_id].iloc[0]
            grade = int(action["grade"])
            if grade < int(replacement_book["grade_min"]) or grade > int(replacement_book["grade_max"]):
                raise ValueError("Replacement title violates the student's grade-band guardrail.")
            if not bool(replacement_book["district_suitable"]):
                raise ValueError("Replacement title violates the district suitability guardrail.")
            working = working.loc[
                ~(
                    (working["student_id"] == student_id)
                    & (working["book_id"].isin([book_id, replacement_id]))
                )
            ].copy()
            replacement_row = {
                "student_id": student_id,
                "book_id": replacement_id,
                "title": replacement_book["title"],
                "author": replacement_book["author"],
                "genre": replacement_book["genre"],
                "availability": replacement_book["availability"],
                "cf_score": 0.0,
                "content_score": 0.45,
                "popularity_score": 0.3,
                "final_score": 0.55,
                "strategy": "librarian_override",
                "anchor_title": action.get("anchor_title", "librarian curation"),
                "history_count": 0,
                "confidence_band": "staff_curated",
                "review_state": "replaced",
                "explanation": f"A librarian swapped in {replacement_book['title']} to better fit local context for this student.",
                "rank": 0.5,
                "librarian_action": "replaced",
            }
            for field in ["student_name", "school_id", "school_name", "grade", "homeroom"]:
                replacement_row[field] = action[field]
            working = pd.concat([working, pd.DataFrame([replacement_row])], ignore_index=True)

    working = working.sort_values(["student_id", "rank", "final_score"], ascending=[True, True, False]).copy()
    working["rank"] = working.groupby("student_id").cumcount() + 1
    working["display_state"] = working["review_state"].replace({"auto_published": "Auto-published", "needs_review": "Needs review", "approved": "Approved", "pinned": "Pinned", "replaced": "Replaced"})
    return working


def _build_debug_log(recommendations: pd.DataFrame, blocked: pd.DataFrame) -> pd.DataFrame:
    rec_log = recommendations[["student_name", "title", "strategy", "cf_score", "content_score", "popularity_score", "final_score", "review_state"]].copy()
    rec_log["event_type"] = "recommended"
    rec_log["detail"] = rec_log["strategy"]
    if blocked.empty:
        return rec_log
    blocked_log = blocked[["student_id", "title", "blocked_reason", "final_score"]].copy()
    blocked_log = blocked_log.merge(recommendations[["student_id", "student_name"]].drop_duplicates(), on="student_id", how="left")
    blocked_log["event_type"] = "guardrail"
    blocked_log["detail"] = blocked_log["blocked_reason"]
    blocked_log["strategy"] = "blocked"
    blocked_log["cf_score"] = 0.0
    blocked_log["content_score"] = 0.0
    blocked_log["popularity_score"] = 0.0
    blocked_log["review_state"] = "blocked"
    blocked_log = blocked_log[["student_name", "title", "strategy", "cf_score", "content_score", "popularity_score", "final_score", "review_state", "event_type", "detail"]]
    return pd.concat([rec_log, blocked_log], ignore_index=True)


def _build_school_metrics(data: DemoData, recommendations: pd.DataFrame) -> pd.DataFrame:
    recommendation_counts = recommendations.groupby("school_id").size().rename("recommendation_volume")
    exposure = recommendations.groupby("school_id")["student_id"].nunique().rename("students_exposed")
    student_counts = data.students.groupby("school_id").size().rename("student_count")
    needs_review = recommendations.loc[recommendations["review_state"] == "needs_review"].groupby("school_id").size().rename("needs_review_count")
    auto_published = recommendations.loc[recommendations["review_state"] == "auto_published"].groupby("school_id").size().rename("auto_published_count")

    school_metrics = pd.concat([student_counts, recommendation_counts, exposure, needs_review, auto_published], axis=1).fillna(0).reset_index()
    school_metrics = school_metrics.merge(data.schools, on="school_id", how="left")
    school_metrics["exposure_rate"] = (school_metrics["students_exposed"] / school_metrics["student_count"]).round(2)
    school_metrics["approval_rate"] = (1 - (school_metrics["needs_review_count"] / school_metrics["recommendation_volume"].replace(0, 1))).round(2)
    school_metrics["override_rate"] = (school_metrics["needs_review_count"] / school_metrics["recommendation_volume"].replace(0, 1) * 0.4).round(2)
    school_metrics["checkout_lift_pct"] = (
        6 + (school_metrics["exposure_rate"] * 8) + (school_metrics["approval_rate"] * 5)
    ).round(1)
    return school_metrics.sort_values("checkout_lift_pct", ascending=False).reset_index(drop=True)


def _build_weekly_metrics(school_metrics: pd.DataFrame) -> pd.DataFrame:
    weeks = pd.DataFrame({"week": list(range(1, 9))})
    rows = []
    for _, school in school_metrics.iterrows():
        for week in weeks["week"]:
            lift = max(0.0, school["checkout_lift_pct"] - 4 + (week * 0.7))
            rows.append(
                {
                    "school_id": school["school_id"],
                    "school_name": school["school_name"],
                    "week": week,
                    "checkout_lift_pct": round(lift, 1),
                    "exposure_rate": school["exposure_rate"],
                    "approval_rate": school["approval_rate"],
                }
            )
    return pd.DataFrame(rows)