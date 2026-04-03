from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class RecommendationResult:
    recommendations: pd.DataFrame
    blocked: pd.DataFrame


class HybridRecommender:
    def __init__(self, catalog: pd.DataFrame, students: pd.DataFrame, checkouts: pd.DataFrame) -> None:
        self.catalog = catalog.copy()
        self.students = students.copy()
        self.checkouts = checkouts.copy()
        self.catalog_index = self.catalog.set_index("book_id")
        self.student_index = self.students.set_index("student_id")
        self.user_item = self._build_user_item_matrix()
        self.student_similarity = pd.DataFrame(
            cosine_similarity(self.user_item),
            index=self.user_item.index,
            columns=self.user_item.index,
        )
        self.book_similarity = self._build_book_similarity()
        self.grade_popularity = self._build_grade_popularity()

    def _build_user_item_matrix(self) -> pd.DataFrame:
        matrix = (
            self.checkouts.assign(value=1)
            .pivot_table(index="student_id", columns="book_id", values="value", fill_value=0)
            .reindex(index=self.students["student_id"], columns=self.catalog["book_id"], fill_value=0)
        )
        return matrix.astype(float)

    def _build_book_similarity(self) -> pd.DataFrame:
        text = (
            self.catalog["title"]
            + " "
            + self.catalog["author"]
            + " "
            + self.catalog["genre"]
            + " "
            + self.catalog["series"]
            + " "
            + self.catalog["description"]
        )
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(text)
        similarity = cosine_similarity(matrix)
        return pd.DataFrame(similarity, index=self.catalog["book_id"], columns=self.catalog["book_id"])

    def _build_grade_popularity(self) -> pd.DataFrame:
        merged = self.checkouts.merge(self.students[["student_id", "grade"]], on="student_id", how="left")
        counts = merged.groupby(["grade", "book_id"]).size().reset_index(name="checkout_count")
        max_by_grade = counts.groupby("grade")["checkout_count"].transform("max").replace(0, 1)
        counts["popularity_score"] = counts["checkout_count"] / max_by_grade
        return counts

    def recommend_for_student(self, student_id: str, top_n: int = 5) -> RecommendationResult:
        student = self.student_index.loc[student_id]
        history = self._student_history(student_id)
        candidate_rows: list[dict] = []
        blocked_rows: list[dict] = []
        history_count = len(history)

        for book_id, book in self.catalog_index.iterrows():
            if book_id in history:
                continue

            cf_score = self._collaborative_score(student_id, book_id)
            content_score, anchor_title = self._content_score(history, book_id)
            popularity_score = self._popularity_score(student["grade"], book_id)
            final_score, strategy = self._blend_scores(history_count, cf_score, content_score, popularity_score)

            row = {
                "student_id": student_id,
                "book_id": book_id,
                "title": book["title"],
                "author": book["author"],
                "genre": book["genre"],
                "availability": book["availability"],
                "cf_score": round(cf_score, 4),
                "content_score": round(content_score, 4),
                "popularity_score": round(popularity_score, 4),
                "final_score": round(final_score, 4),
                "strategy": strategy,
                "anchor_title": anchor_title,
                "history_count": history_count,
            }
            blocked_reason = self._guardrail_reason(student["grade"], book)
            if blocked_reason:
                row["blocked_reason"] = blocked_reason
                blocked_rows.append(row)
                continue

            row["confidence_band"] = self._confidence_band(final_score, history_count)
            row["review_state"] = self._initial_review_state(history_count, row["confidence_band"])
            candidate_rows.append(row)

        recommendations = pd.DataFrame(candidate_rows).sort_values(
            ["final_score", "cf_score", "content_score", "popularity_score"],
            ascending=False,
        )
        recommendations = recommendations.head(top_n).reset_index(drop=True)
        recommendations["rank"] = np.arange(1, len(recommendations) + 1)

        if blocked_rows:
            blocked = pd.DataFrame(blocked_rows).sort_values("final_score", ascending=False).reset_index(drop=True)
        else:
            blocked = pd.DataFrame(columns=[
                "student_id",
                "book_id",
                "title",
                "author",
                "genre",
                "availability",
                "cf_score",
                "content_score",
                "popularity_score",
                "final_score",
                "strategy",
                "anchor_title",
                "history_count",
                "blocked_reason",
            ])
        return RecommendationResult(recommendations=recommendations, blocked=blocked)

    def _student_history(self, student_id: str) -> list[str]:
        return self.checkouts.loc[self.checkouts["student_id"] == student_id, "book_id"].tolist()

    def _collaborative_score(self, student_id: str, book_id: str) -> float:
        weights = self.student_similarity.loc[student_id].copy()
        weights.loc[student_id] = 0.0
        borrowed_mask = self.user_item[book_id] > 0
        return float(weights[borrowed_mask].sum())

    def _content_score(self, history: list[str], book_id: str) -> tuple[float, str]:
        if not history:
            return 0.0, "popular books in your grade"
        similarities = self.book_similarity.loc[history, book_id]
        if isinstance(similarities, float):
            anchor_book_id = history[0]
            return similarities, self.catalog_index.loc[anchor_book_id, "title"]
        anchor_book_id = similarities.sort_values(ascending=False).index[0]
        return float(similarities.mean()), self.catalog_index.loc[anchor_book_id, "title"]

    def _popularity_score(self, grade: int, book_id: str) -> float:
        match = self.grade_popularity.loc[
            (self.grade_popularity["grade"].isin([grade - 1, grade, grade + 1]))
            & (self.grade_popularity["book_id"] == book_id),
            "popularity_score",
        ]
        return float(match.max()) if not match.empty else 0.0

    def _blend_scores(self, history_count: int, cf_score: float, content_score: float, popularity_score: float) -> tuple[float, str]:
        if history_count < 2:
            final = (0.2 * cf_score) + (0.45 * content_score) + (0.35 * popularity_score)
            return final, "cold_start"
        if cf_score >= content_score:
            final = (0.55 * cf_score) + (0.3 * content_score) + (0.15 * popularity_score)
            return final, "collaborative"
        final = (0.4 * cf_score) + (0.45 * content_score) + (0.15 * popularity_score)
        return final, "hybrid"

    def _guardrail_reason(self, grade: int, book: pd.Series) -> str | None:
        if grade < int(book["grade_min"]) or grade > int(book["grade_max"]):
            return f"Blocked by grade-band guardrail ({book['grade_min']}-{book['grade_max']})"
        if not bool(book["district_suitable"]):
            return "Blocked by district suitability guardrail"
        return None

    def _confidence_band(self, final_score: float, history_count: int) -> str:
        if history_count >= 2 and final_score >= 0.65:
            return "high"
        if final_score >= 0.35:
            return "medium"
        return "low"

    def _initial_review_state(self, history_count: int, confidence_band: str) -> str:
        if history_count < 2 or confidence_band == "low":
            return "needs_review"
        return "auto_published"