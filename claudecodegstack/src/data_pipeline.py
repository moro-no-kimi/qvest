#!/usr/bin/env python3
"""
Data ingestion and normalization pipeline for the Reading Lift Pilot.

Loads and normalizes Destiny catalog and checkout data for recommendation processing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
from datetime import datetime, timedelta


class DataPipeline:
    """Handles ingestion and normalization of library data."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.books_df = None
        self.students_df = None
        self.checkouts_df = None
        self.interaction_matrix = None

    def load_raw_data(self) -> None:
        """Load raw CSV files from data directory."""
        print("📥 Loading raw data files...")

        # Load books catalog
        books_path = os.path.join(self.data_dir, "books_catalog.csv")
        if os.path.exists(books_path):
            self.books_df = pd.read_csv(books_path)
            print(f"   Loaded {len(self.books_df)} books from catalog")
        else:
            raise FileNotFoundError(f"Books catalog not found at {books_path}")

        # Load students
        students_path = os.path.join(self.data_dir, "students.csv")
        if os.path.exists(students_path):
            self.students_df = pd.read_csv(students_path)
            print(f"   Loaded {len(self.students_df)} students")
        else:
            raise FileNotFoundError(f"Students file not found at {students_path}")

        # Load checkout history
        checkouts_path = os.path.join(self.data_dir, "checkout_history.csv")
        if os.path.exists(checkouts_path):
            self.checkouts_df = pd.read_csv(checkouts_path)
            print(f"   Loaded {len(self.checkouts_df)} checkout records")
        else:
            raise FileNotFoundError(f"Checkout history not found at {checkouts_path}")

    def normalize_books(self) -> pd.DataFrame:
        """Normalize and enrich book metadata."""
        print("📚 Normalizing book metadata...")

        books = self.books_df.copy()

        # Clean and standardize text fields
        books['title'] = books['title'].str.strip()
        books['author'] = books['author'].str.strip()
        books['genre'] = books['genre'].str.strip()

        # Handle missing series information
        books['is_series'] = books['series_name'].notna()
        books['series_name'] = books['series_name'].fillna('')
        books['series_position'] = books['series_position'].fillna(0).astype(int)

        # Create difficulty categories
        books['difficulty'] = pd.cut(
            books['reading_level'],
            bins=[0, 700, 900, 1200],
            labels=['Easy', 'Medium', 'Advanced'],
            include_lowest=True
        )

        # Create length categories
        books['length_category'] = pd.cut(
            books['pages'],
            bins=[0, 150, 250, 400, float('inf')],
            labels=['Short', 'Medium', 'Long', 'Very Long'],
            include_lowest=True
        )

        # Add popularity metrics (will be updated after processing checkouts)
        books['checkout_count'] = 0
        books['avg_checkout_frequency'] = 0.0

        # Create composite genre categories for better recommendations
        books['genre_group'] = books['genre'].map({
            'Fantasy': 'Speculative Fiction',
            'Science Fiction': 'Speculative Fiction',
            'Mystery': 'Thriller/Mystery',
            'Horror': 'Thriller/Mystery',
            'Adventure': 'Action/Adventure',
            'Realistic Fiction': 'Contemporary',
            'Romance': 'Contemporary',
            'Historical Fiction': 'Literary',
            'Biography': 'Non-Fiction',
            'Non-fiction': 'Non-Fiction',
            'Memoir': 'Non-Fiction',
            'Poetry': 'Literary',
            'Dystopian': 'Speculative Fiction',
            'Humor': 'Light Reading',
            'Graphic Novel': 'Visual/Graphic'
        }).fillna('Other')

        print(f"   Normalized {len(books)} books with {books['genre'].nunique()} genres")
        return books

    def normalize_students(self) -> pd.DataFrame:
        """Normalize and enrich student data."""
        print("👥 Normalizing student data...")

        students = self.students_df.copy()

        # Create reading profile categories
        students['reading_profile'] = 'Average'
        students.loc[students['advanced_reader'], 'reading_profile'] = 'Advanced'
        students.loc[students['reluctant_reader'], 'reading_profile'] = 'Reluctant'

        # Add checkout statistics (will be updated after processing checkouts)
        students['total_checkouts'] = 0
        students['unique_genres'] = 0
        students['avg_book_length'] = 0
        students['favorite_genre'] = ''

        print(f"   Normalized {len(students)} students across {students['school'].nunique()} schools")
        return students

    def process_checkout_history(self) -> pd.DataFrame:
        """Process and normalize checkout history."""
        print("📖 Processing checkout history...")

        checkouts = self.checkouts_df.copy()

        # Convert date strings to datetime
        checkouts['checkout_date'] = pd.to_datetime(checkouts['checkout_date'])
        checkouts['return_date'] = pd.to_datetime(checkouts['return_date'])

        # Calculate reading duration
        checkouts['days_checked_out'] = (
            checkouts['return_date'] - checkouts['checkout_date']
        ).dt.days

        # Add recency scoring (more recent checkouts get higher scores)
        max_date = checkouts['checkout_date'].max()
        checkouts['days_since_checkout'] = (
            max_date - checkouts['checkout_date']
        ).dt.days

        # Create recency weight (decays over time)
        checkouts['recency_weight'] = np.exp(-checkouts['days_since_checkout'] / 90)  # 90 day half-life

        # Mark recent vs historical checkouts
        checkouts['is_recent'] = checkouts['days_since_checkout'] <= 30

        print(f"   Processed {len(checkouts)} checkout records")
        print(f"   Date range: {checkouts['checkout_date'].min().date()} to {checkouts['checkout_date'].max().date()}")
        return checkouts

    def build_interaction_matrix(self) -> pd.DataFrame:
        """Build user-item interaction matrix for collaborative filtering."""
        print("🔗 Building interaction matrix...")

        # Create implicit feedback matrix
        # Using checkout frequency with recency weighting
        interactions = (
            self.checkouts_df.groupby(['student_id', 'book_id'])
            .agg({
                'checkout_id': 'count',  # Raw checkout frequency
                'recency_weight': 'sum'   # Recency-weighted score
            })
            .reset_index()
        )

        interactions.columns = ['student_id', 'book_id', 'checkout_count', 'weighted_score']

        # Create pivot table for collaborative filtering
        interaction_matrix = interactions.pivot(
            index='student_id',
            columns='book_id',
            values='weighted_score'
        ).fillna(0)

        print(f"   Built interaction matrix: {interaction_matrix.shape[0]} students × {interaction_matrix.shape[1]} books")
        print(f"   Sparsity: {(interaction_matrix == 0).sum().sum() / interaction_matrix.size:.2%}")

        self.interaction_matrix = interaction_matrix
        return interactions

    def update_popularity_metrics(self) -> None:
        """Update book and student statistics based on checkout history."""
        print("📊 Updating popularity and reading metrics...")

        # Update book popularity metrics
        book_stats = (
            self.checkouts_df.groupby('book_id')
            .agg({
                'checkout_id': 'count',
                'days_checked_out': 'mean',
                'student_id': 'nunique'
            })
            .reset_index()
        )
        book_stats.columns = ['book_id', 'checkout_count', 'avg_days_out', 'unique_readers']

        # Merge with books dataframe (drop existing checkout_count first)
        if 'checkout_count' in self.books_df.columns:
            self.books_df = self.books_df.drop('checkout_count', axis=1)

        self.books_df = self.books_df.merge(book_stats, on='book_id', how='left')
        self.books_df[['checkout_count', 'unique_readers']] = (
            self.books_df[['checkout_count', 'unique_readers']].fillna(0).astype(int)
        )
        self.books_df['avg_days_out'] = self.books_df['avg_days_out'].fillna(0)

        # Calculate checkout frequency (checkouts per week since first checkout)
        first_checkout = self.checkouts_df.groupby('book_id')['checkout_date'].min()
        weeks_available = (
            (self.checkouts_df['checkout_date'].max() - first_checkout).dt.days / 7
        ).fillna(1)

        book_freq = (
            self.books_df.set_index('book_id')['checkout_count'] / weeks_available
        ).fillna(0)

        self.books_df = self.books_df.set_index('book_id')
        self.books_df['avg_checkout_frequency'] = book_freq
        self.books_df = self.books_df.reset_index()

        # Update student reading metrics
        student_stats = self.checkouts_df.merge(
            self.books_df[['book_id', 'genre', 'pages']],
            on='book_id'
        ).groupby('student_id').agg({
            'checkout_id': 'count',
            'genre': lambda x: x.nunique(),
            'pages': 'mean',
            'book_id': 'nunique'
        }).reset_index()

        student_stats.columns = ['student_id', 'total_checkouts', 'unique_genres', 'avg_book_length', 'unique_books']

        # Find favorite genre for each student
        student_genre_counts = (
            self.checkouts_df.merge(self.books_df[['book_id', 'genre']], on='book_id')
            .groupby(['student_id', 'genre']).size()
            .reset_index(name='count')
        )

        favorite_genres = (
            student_genre_counts.loc[student_genre_counts.groupby('student_id')['count'].idxmax()]
            [['student_id', 'genre']]
        )
        favorite_genres.columns = ['student_id', 'favorite_genre']

        # Merge all student stats
        student_stats = student_stats.merge(favorite_genres, on='student_id', how='left')

        # Drop existing columns that might conflict
        cols_to_drop = ['total_checkouts', 'unique_genres', 'avg_book_length', 'favorite_genre']
        for col in cols_to_drop:
            if col in self.students_df.columns:
                self.students_df = self.students_df.drop(col, axis=1)

        self.students_df = self.students_df.merge(student_stats, on='student_id', how='left')

        # Fill missing values
        numeric_cols = ['total_checkouts', 'unique_genres', 'avg_book_length', 'unique_books']
        self.students_df[numeric_cols] = self.students_df[numeric_cols].fillna(0)
        self.students_df['favorite_genre'] = self.students_df['favorite_genre'].fillna('Unknown')

        print(f"   Updated metrics for {len(self.books_df)} books and {len(self.students_df)} students")

    def get_pipeline_summary(self) -> Dict:
        """Get summary statistics of the processed data."""
        return {
            'books': {
                'total': len(self.books_df),
                'genres': self.books_df['genre'].nunique(),
                'with_series': self.books_df['is_series'].sum(),
                'avg_pages': self.books_df['pages'].mean(),
                'most_popular': self.books_df.nlargest(3, 'checkout_count')[['title', 'author', 'checkout_count']].to_dict('records')
            },
            'students': {
                'total': len(self.students_df),
                'schools': self.students_df['school'].nunique(),
                'grades': sorted(self.students_df['grade'].unique()),
                'avg_checkouts': self.students_df['total_checkouts'].mean(),
                'reading_profiles': self.students_df['reading_profile'].value_counts().to_dict()
            },
            'checkouts': {
                'total': len(self.checkouts_df),
                'date_range': f"{self.checkouts_df['checkout_date'].min().date()} to {self.checkouts_df['checkout_date'].max().date()}",
                'avg_duration_days': self.checkouts_df['days_checked_out'].mean(),
                'recent_checkouts': self.checkouts_df['is_recent'].sum()
            },
            'interaction_matrix': {
                'shape': f"{self.interaction_matrix.shape[0]} students × {self.interaction_matrix.shape[1]} books",
                'sparsity': f"{(self.interaction_matrix == 0).sum().sum() / self.interaction_matrix.size:.2%}",
                'non_zero_interactions': (self.interaction_matrix > 0).sum().sum()
            }
        }

    def run_pipeline(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Run the complete data pipeline."""
        print("🚀 Running data ingestion and normalization pipeline...")

        # Load raw data
        self.load_raw_data()

        # Normalize each dataset
        self.books_df = self.normalize_books()
        self.students_df = self.normalize_students()
        self.checkouts_df = self.process_checkout_history()

        # Build interaction matrix
        interactions_df = self.build_interaction_matrix()

        # Update popularity and reading metrics
        self.update_popularity_metrics()

        print("✅ Data pipeline completed successfully!")
        return self.books_df, self.students_df, self.checkouts_df, interactions_df


def main():
    """Test the data pipeline with generated data."""
    pipeline = DataPipeline()

    try:
        books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

        # Print summary
        summary = pipeline.get_pipeline_summary()
        print("\n📈 Pipeline Summary:")
        print(f"Books: {summary['books']['total']} ({summary['books']['genres']} genres)")
        print(f"Students: {summary['students']['total']} across {summary['students']['schools']} schools")
        print(f"Checkouts: {summary['checkouts']['total']} ({summary['checkouts']['date_range']})")
        print(f"Interaction Matrix: {summary['interaction_matrix']['shape']} ({summary['interaction_matrix']['sparsity']} sparse)")

        print(f"\n🔥 Most Popular Books:")
        for book in summary['books']['most_popular']:
            print(f"   {book['title']} by {book['author']} ({book['checkout_count']} checkouts)")

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()