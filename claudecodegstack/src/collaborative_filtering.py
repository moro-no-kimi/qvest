#!/usr/bin/env python3
"""
Collaborative filtering recommendation engine.
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from typing import List, Tuple, Dict
import warnings
warnings.filterwarnings('ignore')


class CollaborativeRecommender:
    """Collaborative filtering using user-item interactions."""

    def __init__(self, n_components: int = 50):
        self.n_components = n_components
        self.svd_model = TruncatedSVD(n_components=n_components, random_state=42)
        self.interaction_matrix = None
        self.user_factors = None
        self.item_factors = None
        self.user_to_idx = {}
        self.book_to_idx = {}
        self.idx_to_user = {}
        self.idx_to_book = {}

    def fit(self, interaction_matrix: pd.DataFrame):
        """Train collaborative filtering model."""
        print("🤝 Training collaborative filtering model...")

        self.interaction_matrix = interaction_matrix

        # Create index mappings
        self.user_to_idx = {user: idx for idx, user in enumerate(interaction_matrix.index)}
        self.book_to_idx = {book: idx for idx, book in enumerate(interaction_matrix.columns)}
        self.idx_to_user = {idx: user for user, idx in self.user_to_idx.items()}
        self.idx_to_book = {idx: book for book, idx in self.book_to_idx.items()}

        # Fit SVD model
        interaction_array = interaction_matrix.values
        self.svd_model.fit(interaction_array)

        # Get user and item factors
        self.user_factors = self.svd_model.transform(interaction_array)
        self.item_factors = self.svd_model.components_.T

        print(f"   Model trained with {len(self.user_to_idx)} users and {len(self.book_to_idx)} books")
        print(f"   Explained variance ratio: {self.svd_model.explained_variance_ratio_.sum():.3f}")

    def get_user_similarities(self, student_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Find most similar users to given student."""
        if student_id not in self.user_to_idx:
            return []

        user_idx = self.user_to_idx[student_id]
        user_vector = self.user_factors[user_idx].reshape(1, -1)

        # Calculate similarities to all other users
        similarities = cosine_similarity(user_vector, self.user_factors)[0]

        # Get top similar users (excluding self)
        similar_indices = np.argsort(similarities)[::-1][1:top_k+1]

        similar_users = [
            (self.idx_to_user[idx], similarities[idx])
            for idx in similar_indices
            if similarities[idx] > 0
        ]

        return similar_users

    def recommend_for_user(self, student_id: str, books_df: pd.DataFrame,
                          n_recommendations: int = 10) -> List[Dict]:
        """Generate collaborative filtering recommendations for a user."""
        if student_id not in self.user_to_idx:
            return []

        user_idx = self.user_to_idx[student_id]

        # Get user's reading history
        user_interactions = self.interaction_matrix.loc[student_id]
        read_books = set(user_interactions[user_interactions > 0].index)

        # Calculate predicted ratings for all books
        user_vector = self.user_factors[user_idx]
        predicted_ratings = np.dot(self.item_factors, user_vector)

        # Create book scores dataframe
        book_scores = pd.DataFrame({
            'book_id': list(self.book_to_idx.keys()),
            'predicted_rating': predicted_ratings
        })

        # Filter out already read books
        book_scores = book_scores[~book_scores['book_id'].isin(read_books)]

        # Get top recommendations
        top_books = book_scores.nlargest(n_recommendations, 'predicted_rating')

        # Enrich with book metadata
        recommendations = []
        for _, row in top_books.iterrows():
            book_info = books_df[books_df['book_id'] == row['book_id']].iloc[0]

            # Find similar users who liked this book
            similar_users = self.get_user_similarities(student_id, top_k=5)
            users_who_liked = []

            for similar_user_id, similarity in similar_users:
                if row['book_id'] in self.book_to_idx:
                    if self.interaction_matrix.loc[similar_user_id, row['book_id']] > 0:
                        users_who_liked.append((similar_user_id, similarity))

            recommendation = {
                'book_id': row['book_id'],
                'title': book_info['title'],
                'author': book_info['author'],
                'genre': book_info['genre'],
                'predicted_rating': row['predicted_rating'],
                'confidence': min(row['predicted_rating'] / 5.0, 1.0),  # Normalize to 0-1
                'similar_users_who_liked': users_who_liked[:3],
                'recommendation_type': 'collaborative'
            }

            recommendations.append(recommendation)

        return recommendations

    def get_book_similarities(self, book_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Find books similar to given book based on user interactions."""
        if book_id not in self.book_to_idx:
            return []

        book_idx = self.book_to_idx[book_id]
        book_vector = self.item_factors[book_idx].reshape(1, -1)

        # Calculate similarities to all other books
        similarities = cosine_similarity(book_vector, self.item_factors)[0]

        # Get top similar books (excluding self)
        similar_indices = np.argsort(similarities)[::-1][1:top_k+1]

        similar_books = [
            (self.idx_to_book[idx], similarities[idx])
            for idx in similar_indices
            if similarities[idx] > 0
        ]

        return similar_books


def main():
    """Test collaborative filtering with processed data."""
    from data_pipeline import DataPipeline

    # Load and process data
    pipeline = DataPipeline()
    books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

    # Initialize and train collaborative recommender
    recommender = CollaborativeRecommender(n_components=30)
    recommender.fit(pipeline.interaction_matrix)

    # Test recommendations for a few students
    test_students = students_df.head(3)['student_id'].tolist()

    print(f"\n🎯 Testing collaborative filtering recommendations...")

    for student_id in test_students:
        print(f"\n📚 Recommendations for {student_id}:")

        # Get student info
        student_info = students_df[students_df['student_id'] == student_id].iloc[0]
        print(f"   Grade {student_info['grade']}, {student_info['school']}")
        print(f"   Reading profile: {student_info['reading_profile']}")
        print(f"   Total checkouts: {student_info['total_checkouts']}")

        # Get recommendations
        recommendations = recommender.recommend_for_user(student_id, books_df, n_recommendations=5)

        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['title']} by {rec['author']}")
            print(f"      Genre: {rec['genre']}, Confidence: {rec['confidence']:.3f}")
            if rec['similar_users_who_liked']:
                similar_count = len(rec['similar_users_who_liked'])
                print(f"      {similar_count} similar students also liked this book")


if __name__ == "__main__":
    main()