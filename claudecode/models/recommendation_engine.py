"""
Hybrid Recommendation Engine for Library System
Combines collaborative filtering, content-based filtering, and policy guardrails
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import sqlite3
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridRecommendationEngine:
    def __init__(self, db_path="data/library_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.user_item_matrix = None
        self.content_vectors = None
        self.books_df = None
        self.students_df = None
        self.checkouts_df = None

    def load_data(self):
        """Load data from database"""
        self.books_df = pd.read_sql_query("SELECT * FROM books", self.conn)
        self.students_df = pd.read_sql_query("SELECT * FROM students", self.conn)
        self.checkouts_df = pd.read_sql_query("SELECT * FROM checkouts", self.conn)
        logger.info(f"Loaded {len(self.books_df)} books, {len(self.students_df)} students, {len(self.checkouts_df)} checkouts")

    def build_user_item_matrix(self):
        """Build user-item interaction matrix for collaborative filtering"""
        # Create interaction matrix (students x books)
        interactions = self.checkouts_df.groupby(['student_id', 'book_id']).size().reset_index(name='interaction_count')

        # Create pivot table
        self.user_item_matrix = interactions.pivot(
            index='student_id',
            columns='book_id',
            values='interaction_count'
        ).fillna(0)

        logger.info(f"Built user-item matrix: {self.user_item_matrix.shape}")

    def build_content_vectors(self):
        """Build content-based feature vectors using book metadata"""
        # Combine text features
        self.books_df['content_features'] = (
            self.books_df['genre'].fillna('') + ' ' +
            self.books_df['series'].fillna('') + ' ' +
            self.books_df['description'].fillna('')
        )

        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.content_vectors = vectorizer.fit_transform(self.books_df['content_features'])
        logger.info(f"Built content vectors: {self.content_vectors.shape}")

    def get_collaborative_recommendations(self, student_id: str, n_recommendations: int = 10) -> List[Tuple[str, float]]:
        """Get collaborative filtering recommendations"""
        if student_id not in self.user_item_matrix.index:
            return []

        # Get user vector
        user_vector = self.user_item_matrix.loc[student_id]

        # Find similar users
        user_similarities = cosine_similarity([user_vector], self.user_item_matrix)[0]
        similar_users = np.argsort(user_similarities)[::-1][1:11]  # Top 10 similar users

        # Get books liked by similar users that this user hasn't read
        user_books = set(user_vector[user_vector > 0].index)
        recommendations = {}

        for similar_user_idx in similar_users:
            similar_user_id = self.user_item_matrix.index[similar_user_idx]
            similar_user_vector = self.user_item_matrix.loc[similar_user_id]
            similarity_score = user_similarities[similar_user_idx]

            for book_id in similar_user_vector[similar_user_vector > 0].index:
                if book_id not in user_books:
                    if book_id not in recommendations:
                        recommendations[book_id] = 0
                    recommendations[book_id] += similarity_score

        # Sort and return top recommendations
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
        return sorted_recs[:n_recommendations]

    def get_content_recommendations(self, student_id: str, n_recommendations: int = 10) -> List[Tuple[str, float]]:
        """Get content-based recommendations"""
        # Get books the student has read
        student_books = self.checkouts_df[self.checkouts_df['student_id'] == student_id]['book_id'].tolist()

        if not student_books:
            # Cold start: recommend popular books for their grade
            student_grade = self.students_df[self.students_df['student_id'] == student_id]['grade'].iloc[0]
            grade_books = self.books_df[
                (self.books_df['grade_min'] <= student_grade) &
                (self.books_df['grade_max'] >= student_grade)
            ]

            # Get most checked out books for this grade
            popular_books = self.checkouts_df[
                self.checkouts_df['book_id'].isin(grade_books['book_id'])
            ]['book_id'].value_counts().head(n_recommendations)

            return [(book_id, count) for book_id, count in popular_books.items()]

        # Get content vectors for books the student has read
        book_indices = [self.books_df[self.books_df['book_id'] == book_id].index[0]
                       for book_id in student_books if book_id in self.books_df['book_id'].values]

        if not book_indices:
            return []

        # Average the content vectors of books the student has read
        user_profile = np.mean(self.content_vectors[book_indices], axis=0)

        # Calculate similarity with all books
        similarities = cosine_similarity(user_profile, self.content_vectors)[0]

        # Get books the student hasn't read
        unread_books = self.books_df[~self.books_df['book_id'].isin(student_books)]
        unread_indices = unread_books.index.tolist()

        # Get top similar books
        recommendations = []
        for idx in unread_indices:
            book_id = self.books_df.iloc[idx]['book_id']
            similarity = similarities[idx]
            recommendations.append((book_id, similarity))

        # Sort by similarity
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:n_recommendations]

    def apply_policy_guardrails(self, student_id: str, recommendations: List[Tuple[str, float]]) -> List[Tuple[str, float, str]]:
        """Apply grade-level and content policy filters"""
        student = self.students_df[self.students_df['student_id'] == student_id].iloc[0]
        student_grade = student['grade']

        filtered_recommendations = []

        for book_id, score in recommendations:
            book = self.books_df[self.books_df['book_id'] == book_id]
            if book.empty:
                continue

            book = book.iloc[0]

            # Check grade appropriateness
            if book['grade_min'] <= student_grade <= book['grade_max']:
                # Check availability
                if book['available_copies'] > 0:
                    filtered_recommendations.append((book_id, score, 'approved'))
                else:
                    filtered_recommendations.append((book_id, score, 'unavailable'))
            else:
                filtered_recommendations.append((book_id, score, 'grade_inappropriate'))

        return filtered_recommendations

    def generate_recommendations(self, student_id: str, n_recommendations: int = 5) -> List[Dict]:
        """Generate hybrid recommendations for a student"""
        # Get collaborative filtering recommendations
        collab_recs = self.get_collaborative_recommendations(student_id, n_recommendations * 2)

        # Get content-based recommendations
        content_recs = self.get_content_recommendations(student_id, n_recommendations * 2)

        # Combine and weight recommendations (70% collaborative, 30% content)
        combined_recs = {}

        for book_id, score in collab_recs:
            combined_recs[book_id] = 0.7 * score

        for book_id, score in content_recs:
            if book_id in combined_recs:
                combined_recs[book_id] += 0.3 * score
            else:
                combined_recs[book_id] = 0.3 * score

        # Convert to list and sort
        recommendations = [(book_id, score) for book_id, score in combined_recs.items()]
        recommendations.sort(key=lambda x: x[1], reverse=True)

        # Apply policy guardrails
        filtered_recs = self.apply_policy_guardrails(student_id, recommendations)

        # Format final recommendations
        final_recommendations = []
        count = 0

        for book_id, score, status in filtered_recs:
            if status == 'approved' and count < n_recommendations:
                book = self.books_df[self.books_df['book_id'] == book_id].iloc[0]

                # Determine recommendation reason
                reason = "collaborative" if book_id in [r[0] for r in collab_recs[:5]] else "content"

                final_recommendations.append({
                    'book_id': book_id,
                    'title': book['title'],
                    'author': book['author'],
                    'genre': book['genre'],
                    'score': score,
                    'reason': reason,
                    'explanation': self.generate_explanation(student_id, book_id, reason),
                    'status': 'pending'
                })
                count += 1

        return final_recommendations

    def generate_explanation(self, student_id: str, book_id: str, reason: str) -> str:
        """Generate plain-English explanation for recommendation"""
        book = self.books_df[self.books_df['book_id'] == book_id].iloc[0]

        if reason == "collaborative":
            return f"Students who enjoyed books like you also borrowed {book['title']} by {book['author']}"
        else:
            # Find a similar book the student has read
            student_books = self.checkouts_df[self.checkouts_df['student_id'] == student_id]['book_id'].tolist()
            if student_books:
                similar_book_id = student_books[0]  # Simplified for demo
                similar_book = self.books_df[self.books_df['book_id'] == similar_book_id]
                if not similar_book.empty:
                    similar_book = similar_book.iloc[0]
                    return f"Because you liked {similar_book['title']}, you might enjoy this {book['genre'].lower()} story"

            return f"This {book['genre'].lower()} book matches your reading interests"

    def fit(self):
        """Train the recommendation models"""
        logger.info("Training recommendation models...")
        self.load_data()
        self.build_user_item_matrix()
        self.build_content_vectors()
        logger.info("Models trained successfully")