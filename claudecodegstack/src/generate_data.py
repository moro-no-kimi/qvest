#!/usr/bin/env python3
"""
Synthetic data generation for Fulton County Reading Lift Pilot POC.

Generates realistic library catalog and checkout data for middle school students.
"""

import pandas as pd
import numpy as np
import json
import random
from datetime import datetime, timedelta
from faker import Faker
import os

fake = Faker()
np.random.seed(42)
random.seed(42)

# Configuration
N_BOOKS = 500
N_STUDENTS = 200
N_SCHOOLS = 5
N_CHECKOUTS = 2000

# Grade levels for middle school
GRADE_LEVELS = [6, 7, 8]

# Popular middle grade genres and themes
GENRES = [
    "Fantasy", "Science Fiction", "Mystery", "Adventure", "Realistic Fiction",
    "Historical Fiction", "Dystopian", "Romance", "Humor", "Horror",
    "Biography", "Non-fiction", "Poetry", "Graphic Novel", "Memoir"
]

# Reading levels (simplified Lexile-like scores)
READING_LEVELS = {
    6: (600, 900),   # Grade 6: 600-900L
    7: (700, 1000),  # Grade 7: 700-1000L
    8: (800, 1100)   # Grade 8: 800-1100L
}

def generate_book_catalog():
    """Generate synthetic book catalog with realistic metadata."""

    books = []

    # Popular middle grade book titles and authors for inspiration
    sample_titles = [
        "The Lightning Thief", "Wonder", "Holes", "The Giver", "Hatchet",
        "Bridge to Terabithia", "The Outsiders", "Freak the Mighty", "The Hunger Games",
        "Harry Potter", "Percy Jackson", "Diary of a Wimpy Kid", "The Maze Runner",
        "Divergent", "The Fault in Our Stars", "Esperanza Rising", "Walk Two Moons",
        "Number the Stars", "Island of the Blue Dolphins", "Where the Red Fern Grows"
    ]

    sample_authors = [
        "Rick Riordan", "R.J. Palacio", "Louis Sachar", "Lois Lowry", "Gary Paulsen",
        "Katherine Paterson", "S.E. Hinton", "Rodman Philbrick", "Suzanne Collins",
        "J.K. Rowling", "Jeff Kinney", "James Dashner", "Veronica Roth", "John Green",
        "Pam Muñoz Ryan", "Sharon Creech", "Lois Lowry", "Scott O'Dell", "Wilson Rawls"
    ]

    # Generate series information
    series_names = [
        "Percy Jackson", "Harry Potter", "Diary of a Wimpy Kid", "The Hunger Games",
        "Divergent", "The Maze Runner", "Wings of Fire", "Dog Man", "Captain Underpants",
        "The Baby-Sitters Club", "Goosebumps", "Magic Tree House", "Hilo"
    ]

    for i in range(N_BOOKS):
        # Randomly decide if this book is part of a series
        is_series = random.random() < 0.3
        series_info = {}

        if is_series:
            series_name = random.choice(series_names)
            series_info = {
                "series_name": series_name,
                "series_position": random.randint(1, 12)
            }

        # Generate grade level and corresponding reading level
        target_grade = random.choice(GRADE_LEVELS)
        min_level, max_level = READING_LEVELS[target_grade]
        reading_level = random.randint(min_level, max_level)

        # Generate realistic book data
        title = fake.catch_phrase() if random.random() > 0.7 else random.choice(sample_titles) + f" {random.randint(1, 5)}"
        author = fake.name() if random.random() > 0.5 else random.choice(sample_authors)

        genre = random.choice(GENRES)
        pages = random.randint(100, 400)

        # Generate description based on genre
        descriptions = {
            "Fantasy": "A magical adventure where young heroes discover hidden powers and face ancient evils.",
            "Science Fiction": "Set in a futuristic world where technology and humanity collide in unexpected ways.",
            "Mystery": "A thrilling puzzle that challenges readers to solve the case alongside the protagonist.",
            "Adventure": "An action-packed journey filled with danger, excitement, and unexpected discoveries.",
            "Realistic Fiction": "A relatable story about growing up and facing real-world challenges.",
            "Historical Fiction": "A compelling tale set against the backdrop of important historical events.",
            "Dystopian": "A thought-provoking story about survival in a society where freedom is under threat.",
            "Romance": "A heartwarming story about first love and the complexities of relationships.",
            "Humor": "A laugh-out-loud funny story that will keep readers entertained from start to finish.",
            "Biography": "The inspiring true story of someone who made a difference in the world."
        }

        book = {
            "book_id": f"book_{i+1:04d}",
            "title": title,
            "author": author,
            "genre": genre,
            "target_grade_min": max(6, target_grade - 1),
            "target_grade_max": min(8, target_grade + 1),
            "reading_level": reading_level,
            "pages": pages,
            "description": descriptions.get(genre, "An engaging story for middle grade readers."),
            "isbn": fake.isbn13(),
            "publication_year": random.randint(2000, 2023),
            "copies_available": random.randint(1, 5),
            **series_info
        }

        books.append(book)

    return pd.DataFrame(books)

def generate_students():
    """Generate synthetic student data."""
    students = []

    school_names = [
        "Riverside Middle School",
        "Oak Grove Academy",
        "Brookfield Middle",
        "Pine Valley School",
        "Sunset Ridge Middle"
    ]

    for i in range(N_STUDENTS):
        grade = random.choice(GRADE_LEVELS)
        school = random.choice(school_names)

        # Generate reading personality traits that will influence preferences
        reading_traits = {
            "prefers_series": random.random() < 0.6,
            "prefers_fantasy": random.random() < 0.4,
            "advanced_reader": random.random() < 0.3,  # Reads above grade level
            "reluctant_reader": random.random() < 0.2,  # Prefers shorter books
            "genre_explorer": random.random() < 0.5    # Tries different genres
        }

        student = {
            "student_id": f"student_{i+1:04d}",
            "grade": grade,
            "school": school,
            "reading_level_preference": "above_grade" if reading_traits["advanced_reader"]
                                      else "at_grade" if not reading_traits["reluctant_reader"]
                                      else "below_grade",
            **reading_traits
        }

        students.append(student)

    return pd.DataFrame(students)

def generate_checkout_history(books_df, students_df):
    """Generate realistic checkout history based on student preferences and book attributes."""

    checkouts = []
    checkout_id = 1

    # Create checkout events over the past year
    start_date = datetime.now() - timedelta(days=365)

    for _ in range(N_CHECKOUTS):
        student = students_df.sample(1).iloc[0]

        # Filter books appropriate for this student's grade and preferences
        suitable_books = books_df[
            (books_df['target_grade_min'] <= student['grade']) &
            (books_df['target_grade_max'] >= student['grade'])
        ].copy()

        # Apply student preferences to book selection probabilities
        book_weights = np.ones(len(suitable_books))

        for i, (idx, book) in enumerate(suitable_books.iterrows()):
            weight = 1.0

            # Series preference
            if student['prefers_series'] and 'series_name' in book and pd.notna(book['series_name']):
                weight *= 2.0
            elif not student['prefers_series'] and 'series_name' in book and pd.notna(book['series_name']):
                weight *= 0.5

            # Fantasy preference
            if student['prefers_fantasy'] and book['genre'] == 'Fantasy':
                weight *= 3.0
            elif not student['prefers_fantasy'] and book['genre'] == 'Fantasy':
                weight *= 0.3

            # Reading level preferences
            if student['advanced_reader'] and book['reading_level'] > READING_LEVELS[student['grade']][1]:
                weight *= 1.5
            elif student['reluctant_reader'] and book['pages'] < 200:
                weight *= 2.0
            elif student['reluctant_reader'] and book['pages'] > 300:
                weight *= 0.3

            # Genre exploration
            if student['genre_explorer']:
                if book['genre'] in ['Science Fiction', 'Mystery', 'Historical Fiction']:
                    weight *= 1.3

            book_weights[i] = weight

        # Normalize weights and select book
        if len(suitable_books) > 0 and book_weights.sum() > 0:
            book_weights = book_weights / book_weights.sum()
            selected_book_idx = np.random.choice(len(suitable_books), p=book_weights)
            selected_book = suitable_books.iloc[selected_book_idx]

            # Generate checkout date
            checkout_date = start_date + timedelta(days=random.randint(0, 365))

            checkout = {
                "checkout_id": checkout_id,
                "student_id": student['student_id'],
                "book_id": selected_book['book_id'],
                "checkout_date": checkout_date.strftime("%Y-%m-%d"),
                "return_date": (checkout_date + timedelta(days=random.randint(7, 21))).strftime("%Y-%m-%d"),
                "school": student['school']
            }

            checkouts.append(checkout)
            checkout_id += 1

    return pd.DataFrame(checkouts)

def main():
    """Generate all synthetic datasets."""
    print("Generating synthetic data for Fulton County Reading Lift Pilot...")

    # Create data directory
    os.makedirs("data", exist_ok=True)

    # Generate datasets
    print("📚 Generating book catalog...")
    books_df = generate_book_catalog()
    books_df.to_csv("data/books_catalog.csv", index=False)
    print(f"   Generated {len(books_df)} books")

    print("👥 Generating student data...")
    students_df = generate_students()
    students_df.to_csv("data/students.csv", index=False)
    print(f"   Generated {len(students_df)} students across {N_SCHOOLS} schools")

    print("📖 Generating checkout history...")
    checkouts_df = generate_checkout_history(books_df, students_df)
    checkouts_df.to_csv("data/checkout_history.csv", index=False)
    print(f"   Generated {len(checkouts_df)} checkout events")

    # Generate summary statistics
    print("\n📊 Dataset Summary:")
    print(f"Books: {len(books_df)}")
    print(f"Students: {len(students_df)}")
    print(f"Checkouts: {len(checkouts_df)}")
    print(f"Genres: {books_df['genre'].nunique()}")
    print(f"Schools: {students_df['school'].nunique()}")
    print(f"Grade levels: {sorted(students_df['grade'].unique())}")

    # Show popular books
    popular_books = (checkouts_df.groupby('book_id').size()
                    .reset_index(name='checkout_count')
                    .merge(books_df, on='book_id')
                    .nlargest(5, 'checkout_count'))

    print(f"\n🔥 Most Popular Books:")
    for _, book in popular_books.iterrows():
        print(f"   {book['title']} by {book['author']} ({book['checkout_count']} checkouts)")

    print(f"\n✅ Synthetic data generated successfully!")
    print(f"   Files saved to data/ directory")

if __name__ == "__main__":
    main()