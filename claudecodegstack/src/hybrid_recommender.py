#!/usr/bin/env python3
"""
Hybrid recommendation engine combining collaborative filtering, content-based, and policy guardrails.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from collaborative_filtering import CollaborativeRecommender
from content_based import ContentBasedRecommender
from policy_guardrails import PolicyGuardrails


@dataclass
class RecommendationConfig:
    """Configuration for hybrid recommendation engine."""
    collab_weight: float = 0.5      # Weight for collaborative filtering
    content_weight: float = 0.3     # Weight for content-based
    popularity_weight: float = 0.2  # Weight for popularity boost

    min_collab_interactions: int = 3  # Minimum checkouts for collaborative filtering
    diversity_factor: float = 0.3     # How much to promote genre diversity

    n_recommendations: int = 10
    require_availability: bool = True


class HybridRecommender:
    """Unified recommendation engine combining multiple approaches."""

    def __init__(self, config: RecommendationConfig = None):
        self.config = config or RecommendationConfig()

        self.collaborative_model = CollaborativeRecommender()
        self.content_model = ContentBasedRecommender()
        self.policy_engine = PolicyGuardrails()

        self.is_trained = False
        self.books_df = None
        self.students_df = None

    def fit(self, books_df: pd.DataFrame, students_df: pd.DataFrame,
            interaction_matrix: pd.DataFrame):
        """Train all recommendation models."""
        print("🎯 Training hybrid recommendation engine...")

        self.books_df = books_df
        self.students_df = students_df

        # Train collaborative filtering model
        self.collaborative_model.fit(interaction_matrix)

        # Train content-based model
        self.content_model.fit(books_df)

        self.is_trained = True
        print("   ✅ All models trained successfully")

    def _get_collaborative_recommendations(self, student_id: str,
                                        student_history: List[str]) -> List[Dict]:
        """Get recommendations from collaborative filtering."""
        if len(student_history) < self.config.min_collab_interactions:
            return []  # Not enough data for collaborative filtering

        return self.collaborative_model.recommend_for_user(
            student_id, self.books_df, n_recommendations=20
        )

    def _get_content_recommendations(self, student_id: str,
                                   student_history: List[str]) -> List[Dict]:
        """Get recommendations from content-based filtering."""
        return self.content_model.recommend_for_user(
            student_id, student_history, self.books_df, n_recommendations=20
        )

    def _get_popularity_boost(self, book_id: str) -> float:
        """Calculate popularity boost for a book."""
        book_info = self.books_df[self.books_df['book_id'] == book_id]
        if len(book_info) == 0:
            return 0.0

        book = book_info.iloc[0]

        # Normalize checkout count (0-1 scale)
        max_checkouts = self.books_df['checkout_count'].max()
        if max_checkouts > 0:
            popularity_score = book['checkout_count'] / max_checkouts
        else:
            popularity_score = 0.0

        # Consider recency - newer books get slight boost
        current_year = 2024
        book_age = max(1, current_year - book.get('publication_year', 2000))
        recency_factor = min(1.0, 5.0 / book_age)  # Books from last 5 years get full boost

        return popularity_score * recency_factor

    def _calculate_diversity_penalty(self, recommendations: List[Dict],
                                   new_book_genre: str) -> float:
        """Calculate penalty for lack of genre diversity."""
        if not recommendations:
            return 0.0

        # Count existing genres
        existing_genres = [rec.get('genre', '') for rec in recommendations]
        genre_counts = {}
        for genre in existing_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

        # Penalty increases with genre repetition
        genre_frequency = genre_counts.get(new_book_genre, 0)
        penalty = min(0.5, genre_frequency * 0.1)  # Max 50% penalty

        return penalty

    def _combine_scores(self, collab_recs: List[Dict], content_recs: List[Dict],
                       student_grade: int) -> List[Dict]:
        """Combine and rank recommendations from different sources."""

        # Create unified book score dictionary
        combined_scores = {}

        # Add collaborative filtering scores
        for rec in collab_recs:
            book_id = rec['book_id']
            collab_score = rec.get('confidence', 0.0)

            combined_scores[book_id] = {
                'book_id': book_id,
                'title': rec['title'],
                'author': rec['author'],
                'genre': rec['genre'],
                'collab_score': collab_score,
                'content_score': 0.0,
                'popularity_boost': self._get_popularity_boost(book_id),
                'sources': ['collaborative']
            }

        # Add content-based scores
        for rec in content_recs:
            book_id = rec['book_id']
            content_score = rec.get('confidence', 0.0)

            if book_id in combined_scores:
                combined_scores[book_id]['content_score'] = content_score
                combined_scores[book_id]['sources'].append('content_based')
            else:
                combined_scores[book_id] = {
                    'book_id': book_id,
                    'title': rec['title'],
                    'author': rec['author'],
                    'genre': rec['genre'],
                    'collab_score': 0.0,
                    'content_score': content_score,
                    'popularity_boost': self._get_popularity_boost(book_id),
                    'sources': ['content_based']
                }

        # Calculate combined scores with diversity considerations
        final_recommendations = []

        for book_id, scores in combined_scores.items():
            # Weighted combination of different signals
            combined_score = (
                scores['collab_score'] * self.config.collab_weight +
                scores['content_score'] * self.config.content_weight +
                scores['popularity_boost'] * self.config.popularity_weight
            )

            # Apply diversity penalty
            diversity_penalty = self._calculate_diversity_penalty(
                final_recommendations, scores['genre']
            )
            combined_score *= (1 - diversity_penalty * self.config.diversity_factor)

            # Create final recommendation object
            recommendation = {
                'book_id': book_id,
                'title': scores['title'],
                'author': scores['author'],
                'genre': scores['genre'],
                'combined_score': combined_score,
                'collab_score': scores['collab_score'],
                'content_score': scores['content_score'],
                'popularity_boost': scores['popularity_boost'],
                'sources': scores['sources'],
                'confidence': min(combined_score, 1.0),
                'recommendation_type': 'hybrid'
            }

            final_recommendations.append(recommendation)

        # Sort by combined score
        final_recommendations.sort(key=lambda x: x['combined_score'], reverse=True)

        return final_recommendations

    def recommend_for_user(self, student_id: str, n_recommendations: int = None) -> List[Dict]:
        """Generate hybrid recommendations for a student."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making recommendations")

        n_recs = n_recommendations or self.config.n_recommendations

        # Get student information
        student_info = self.students_df[self.students_df['student_id'] == student_id]
        if len(student_info) == 0:
            raise ValueError(f"Student {student_id} not found")

        student = student_info.iloc[0]
        student_grade = student['grade']

        # Get student reading history
        if hasattr(self.collaborative_model, 'interaction_matrix') and student_id in self.collaborative_model.interaction_matrix.index:
            user_interactions = self.collaborative_model.interaction_matrix.loc[student_id]
            student_history = list(user_interactions[user_interactions > 0].index)
        else:
            student_history = []

        print(f"📚 Generating hybrid recommendations for {student_id}")
        print(f"   Grade: {student_grade}, Reading history: {len(student_history)} books")

        # Get recommendations from different sources
        collab_recs = self._get_collaborative_recommendations(student_id, student_history)
        content_recs = self._get_content_recommendations(student_id, student_history)

        print(f"   Collaborative: {len(collab_recs)}, Content-based: {len(content_recs)}")

        # Combine and rank recommendations
        combined_recs = self._combine_scores(collab_recs, content_recs, student_grade)

        # Apply policy guardrails
        filtered_recs = self.policy_engine.filter_recommendations(
            combined_recs, student_grade, student_history, self.books_df
        )

        print(f"   After policy filtering: {len(filtered_recs)}")

        # Return top N recommendations
        return filtered_recs[:n_recs]

    def get_recommendation_explanation(self, recommendation: Dict,
                                     student_history: List[str]) -> str:
        """Generate explanation for why a book was recommended."""
        sources = recommendation.get('sources', [])

        explanations = []

        if 'collaborative' in sources and recommendation.get('collab_score', 0) > 0:
            explanations.append("students with similar reading tastes also liked this")

        if 'content_based' in sources and recommendation.get('content_score', 0) > 0:
            # Get detailed content explanation
            content_explanation = self.content_model.explain_recommendation(
                recommendation['book_id'], student_history
            )
            explanations.append(content_explanation.lower())

        if recommendation.get('popularity_boost', 0) > 0.5:
            explanations.append("this is a popular choice among students")

        if not explanations:
            explanations.append("this book matches your reading profile")

        return "; ".join(explanations[:2])  # Limit to 2 main explanations

    def get_system_stats(self) -> Dict:
        """Get statistics about the recommendation system performance."""
        if not self.is_trained:
            return {"status": "not_trained"}

        # Get basic model stats
        n_students = len(self.collaborative_model.user_to_idx) if hasattr(self.collaborative_model, 'user_to_idx') else 0
        n_books = len(self.collaborative_model.book_to_idx) if hasattr(self.collaborative_model, 'book_to_idx') else 0

        # Calculate coverage statistics
        available_books = self.books_df[self.books_df['copies_available'] > 0]['book_id'].nunique()
        total_books = len(self.books_df)

        return {
            "status": "trained",
            "students": n_students,
            "books": n_books,
            "available_books": available_books,
            "total_books": total_books,
            "availability_rate": available_books / total_books if total_books > 0 else 0,
            "config": {
                "collab_weight": self.config.collab_weight,
                "content_weight": self.config.content_weight,
                "popularity_weight": self.config.popularity_weight
            }
        }


def main():
    """Test hybrid recommendation system."""
    from data_pipeline import DataPipeline

    # Load data
    pipeline = DataPipeline()
    books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

    # Initialize hybrid recommender
    config = RecommendationConfig(
        collab_weight=0.4,
        content_weight=0.4,
        popularity_weight=0.2,
        diversity_factor=0.3
    )

    recommender = HybridRecommender(config)
    recommender.fit(books_df, students_df, pipeline.interaction_matrix)

    # Test with different student types
    test_students = [
        students_df[students_df['total_checkouts'] > 8].iloc[0],  # High activity
        students_df[students_df['total_checkouts'] == 0].iloc[0] if len(students_df[students_df['total_checkouts'] == 0]) > 0 else students_df.iloc[1],  # Cold start
        students_df.iloc[2]  # Average
    ]

    for student in test_students:
        student_id = student['student_id']

        print(f"\n🎯 Hybrid Recommendations for {student_id}")
        print(f"   Grade: {student['grade']}, Profile: {student['reading_profile']}")
        print(f"   Total checkouts: {student['total_checkouts']}")

        # Get recommendations
        recommendations = recommender.recommend_for_user(student_id, n_recommendations=5)

        # Get student history for explanations
        student_checkouts = checkouts_df[checkouts_df['student_id'] == student_id]['book_id'].tolist()

        print(f"\n📚 Top 5 Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            status = "🟡 REVIEW" if rec.get('requires_review', False) else "✅ AUTO"
            explanation = recommender.get_recommendation_explanation(rec, student_checkouts)

            print(f"   {i}. {rec['title']} by {rec['author']} - {status}")
            print(f"      Score: {rec['combined_score']:.3f} (collab: {rec['collab_score']:.3f}, content: {rec['content_score']:.3f})")
            print(f"      Sources: {', '.join(rec['sources'])}")
            print(f"      Why: {explanation}")

    # Print system stats
    stats = recommender.get_system_stats()
    print(f"\n📊 System Statistics:")
    print(f"   Students: {stats['students']}, Books: {stats['books']}")
    print(f"   Availability: {stats['availability_rate']:.1%}")
    print(f"   Weights: collab={stats['config']['collab_weight']}, content={stats['config']['content_weight']}, popularity={stats['config']['popularity_weight']}")


if __name__ == "__main__":
    main()