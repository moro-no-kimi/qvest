#!/usr/bin/env python3
"""
Content-based recommendation engine using book metadata.
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')


class ContentBasedRecommender:
    """Content-based filtering using book features."""

    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        self.scaler = StandardScaler()
        self.feature_matrix = None
        self.similarity_matrix = None
        self.book_to_idx = {}
        self.idx_to_book = {}
        self.books_df = None

    def prepare_book_features(self, books_df: pd.DataFrame) -> np.ndarray:
        """Create feature matrix from book metadata."""
        print("📖 Preparing content-based features...")

        self.books_df = books_df.copy()

        # Create mappings
        self.book_to_idx = {book_id: idx for idx, book_id in enumerate(books_df['book_id'])}
        self.idx_to_book = {idx: book_id for book_id, idx in self.book_to_idx.items()}

        # Combine text features for TF-IDF
        books_df['combined_text'] = (
            books_df['title'].fillna('') + ' ' +
            books_df['author'].fillna('') + ' ' +
            books_df['genre'].fillna('') + ' ' +
            books_df['description'].fillna('') + ' ' +
            books_df['series_name'].fillna('')
        )

        # Generate TF-IDF features
        tfidf_features = self.tfidf_vectorizer.fit_transform(books_df['combined_text'])

        # Prepare numerical features
        numerical_features = []

        # Reading level (normalized)
        reading_levels = books_df['reading_level'].values.reshape(-1, 1)
        reading_levels_scaled = self.scaler.fit_transform(reading_levels)
        numerical_features.append(reading_levels_scaled)

        # Pages (normalized)
        pages = books_df['pages'].values.reshape(-1, 1)
        pages_scaled = StandardScaler().fit_transform(pages)
        numerical_features.append(pages_scaled)

        # Publication year (normalized)
        pub_years = books_df['publication_year'].values.reshape(-1, 1)
        pub_years_scaled = StandardScaler().fit_transform(pub_years)
        numerical_features.append(pub_years_scaled)

        # One-hot encode categorical features
        genre_dummies = pd.get_dummies(books_df['genre'], prefix='genre')
        genre_group_dummies = pd.get_dummies(books_df['genre_group'], prefix='group')
        difficulty_dummies = pd.get_dummies(books_df['difficulty'], prefix='difficulty')

        # Series indicator
        series_indicator = books_df['is_series'].astype(int).values.reshape(-1, 1)

        # Combine all features
        categorical_features = np.hstack([
            genre_dummies.values,
            genre_group_dummies.values,
            difficulty_dummies.values,
            series_indicator
        ])

        # Combine TF-IDF, numerical, and categorical features
        combined_features = np.hstack([
            tfidf_features.toarray(),
            np.hstack(numerical_features),
            categorical_features
        ])

        print(f"   Created feature matrix: {combined_features.shape}")
        print(f"   TF-IDF features: {tfidf_features.shape[1]}")
        print(f"   Numerical features: {len(numerical_features)}")
        print(f"   Categorical features: {categorical_features.shape[1]}")

        return combined_features

    def fit(self, books_df: pd.DataFrame):
        """Train content-based model."""
        self.feature_matrix = self.prepare_book_features(books_df)

        # Calculate similarity matrix
        print("🔍 Computing book similarity matrix...")
        self.similarity_matrix = cosine_similarity(self.feature_matrix)

        print(f"   Similarity matrix shape: {self.similarity_matrix.shape}")

    def get_similar_books(self, book_id: str, top_k: int = 10,
                         exclude_same_author: bool = False) -> List[Tuple[str, float]]:
        """Find books similar to given book."""
        if book_id not in self.book_to_idx:
            return []

        book_idx = self.book_to_idx[book_id]
        similarities = self.similarity_matrix[book_idx]

        # Get indices of most similar books (excluding self)
        similar_indices = np.argsort(similarities)[::-1][1:]

        similar_books = []
        book_info = self.books_df[self.books_df['book_id'] == book_id].iloc[0]

        for idx in similar_indices:
            if len(similar_books) >= top_k:
                break

            similar_book_id = self.idx_to_book[idx]
            similarity_score = similarities[idx]

            # Skip if same author (optional)
            if exclude_same_author:
                similar_book_info = self.books_df[self.books_df['book_id'] == similar_book_id].iloc[0]
                if similar_book_info['author'] == book_info['author']:
                    continue

            if similarity_score > 0.1:  # Minimum similarity threshold
                similar_books.append((similar_book_id, similarity_score))

        return similar_books

    def recommend_for_user(self, student_id: str, student_history: List[str],
                          books_df: pd.DataFrame, n_recommendations: int = 10) -> List[Dict]:
        """Generate content-based recommendations for a user."""
        if not student_history:
            return self._cold_start_recommendations(books_df, n_recommendations)

        # Get similarities for all books in user's history
        all_similarities = {}

        for book_id in student_history:
            if book_id in self.book_to_idx:
                similar_books = self.get_similar_books(book_id, top_k=50)

                for similar_book_id, similarity in similar_books:
                    if similar_book_id not in student_history:  # Don't recommend already read books
                        if similar_book_id not in all_similarities:
                            all_similarities[similar_book_id] = []
                        all_similarities[similar_book_id].append(similarity)

        # Aggregate similarities (average)
        book_scores = []
        for book_id, similarities in all_similarities.items():
            avg_similarity = np.mean(similarities)
            max_similarity = np.max(similarities)
            confidence = min(avg_similarity, 1.0)

            book_info = books_df[books_df['book_id'] == book_id]
            if len(book_info) > 0:
                book_info = book_info.iloc[0]

                book_scores.append({
                    'book_id': book_id,
                    'title': book_info['title'],
                    'author': book_info['author'],
                    'genre': book_info['genre'],
                    'similarity_score': avg_similarity,
                    'max_similarity': max_similarity,
                    'confidence': confidence,
                    'recommendation_type': 'content_based'
                })

        # Sort by similarity score and return top N
        book_scores.sort(key=lambda x: x['similarity_score'], reverse=True)
        return book_scores[:n_recommendations]

    def _cold_start_recommendations(self, books_df: pd.DataFrame,
                                   n_recommendations: int = 10) -> List[Dict]:
        """Provide recommendations for users with no history (cold start)."""
        # For cold start, recommend popular books across different genres
        popular_books = books_df.nlargest(n_recommendations * 2, 'checkout_count')

        # Ensure genre diversity
        recommendations = []
        seen_genres = set()

        for _, book in popular_books.iterrows():
            if len(recommendations) >= n_recommendations:
                break

            # Try to include different genres
            if book['genre'] not in seen_genres or len(seen_genres) >= 5:
                recommendations.append({
                    'book_id': book['book_id'],
                    'title': book['title'],
                    'author': book['author'],
                    'genre': book['genre'],
                    'similarity_score': 0.0,
                    'confidence': 0.8,  # High confidence for popular books
                    'recommendation_type': 'cold_start_popular'
                })
                seen_genres.add(book['genre'])

        return recommendations

    def explain_recommendation(self, recommended_book_id: str,
                             user_history: List[str]) -> str:
        """Generate explanation for why a book was recommended."""
        if not user_history or recommended_book_id not in self.book_to_idx:
            return "This book is popular among students like you."

        # Find which book(s) in history are most similar to recommendation
        max_similarity = 0
        most_similar_book = None

        for history_book_id in user_history:
            if history_book_id in self.book_to_idx:
                similar_books = self.get_similar_books(history_book_id, top_k=20)
                for book_id, similarity in similar_books:
                    if book_id == recommended_book_id and similarity > max_similarity:
                        max_similarity = similarity
                        most_similar_book = history_book_id

        if most_similar_book:
            history_book = self.books_df[self.books_df['book_id'] == most_similar_book].iloc[0]
            recommended_book = self.books_df[self.books_df['book_id'] == recommended_book_id].iloc[0]

            # Create explanation based on similarity factors
            explanations = []

            if history_book['genre'] == recommended_book['genre']:
                explanations.append(f"same genre ({recommended_book['genre']})")

            if history_book['author'] == recommended_book['author']:
                explanations.append("same author")

            if history_book['series_name'] == recommended_book['series_name'] and history_book['is_series']:
                explanations.append("same series")

            if abs(history_book['reading_level'] - recommended_book['reading_level']) < 100:
                explanations.append("similar reading level")

            if explanations:
                return f"Because you liked '{history_book['title']}', you might enjoy this book with {' and '.join(explanations)}."

        return f"This book has similar themes to books you've enjoyed."


def main():
    """Test content-based recommendations."""
    from data_pipeline import DataPipeline

    # Load and process data
    pipeline = DataPipeline()
    books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

    # Initialize and train content-based recommender
    recommender = ContentBasedRecommender()
    recommender.fit(books_df)

    # Test with a student who has reading history
    test_student = students_df[students_df['total_checkouts'] > 5].iloc[0]
    student_id = test_student['student_id']

    # Get student's reading history
    student_checkouts = checkouts_df[checkouts_df['student_id'] == student_id]['book_id'].tolist()

    print(f"\n🎯 Testing content-based recommendations for {student_id}:")
    print(f"   Reading history: {len(student_checkouts)} books")

    # Show some books they've read
    history_titles = []
    for book_id in student_checkouts[:3]:
        book_info = books_df[books_df['book_id'] == book_id].iloc[0]
        history_titles.append(f"{book_info['title']} ({book_info['genre']})")
    print(f"   Recently read: {', '.join(history_titles)}")

    # Get recommendations
    recommendations = recommender.recommend_for_user(
        student_id, student_checkouts, books_df, n_recommendations=5
    )

    print(f"\n📚 Content-based recommendations:")
    for i, rec in enumerate(recommendations, 1):
        explanation = recommender.explain_recommendation(rec['book_id'], student_checkouts)
        print(f"   {i}. {rec['title']} by {rec['author']}")
        print(f"      Genre: {rec['genre']}, Confidence: {rec['confidence']:.3f}")
        print(f"      Explanation: {explanation}")


if __name__ == "__main__":
    main()