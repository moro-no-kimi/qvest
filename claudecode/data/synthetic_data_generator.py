"""
Synthetic Data Generator for Fulton County Reading Lift Pilot
Generates realistic library data including books, students, and checkout patterns
"""
import pandas as pd
import numpy as np
import sqlite3
from faker import Faker
import random
from datetime import datetime, timedelta
import json

fake = Faker()

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)
Faker.seed(42)

class SyntheticDataGenerator:
    def __init__(self, db_path="data/library_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def create_tables(self):
        """Create database tables for the library system"""
        cursor = self.conn.cursor()

        # Books table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            book_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            series TEXT,
            grade_min INTEGER,
            grade_max INTEGER,
            lexile_level INTEGER,
            pages INTEGER,
            publication_year INTEGER,
            description TEXT,
            isbn TEXT,
            available_copies INTEGER DEFAULT 1
        )
        ''')

        # Students table (using synthetic IDs for privacy)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            grade INTEGER NOT NULL,
            school_id TEXT NOT NULL,
            reading_level TEXT,
            created_date DATE
        )
        ''')

        # Checkout history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkouts (
            checkout_id TEXT PRIMARY KEY,
            student_id TEXT,
            book_id TEXT,
            checkout_date DATE,
            return_date DATE,
            school_id TEXT,
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (book_id) REFERENCES books (book_id)
        )
        ''')

        # Recommendations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            recommendation_id TEXT PRIMARY KEY,
            student_id TEXT,
            book_id TEXT,
            recommendation_score REAL,
            reason TEXT,
            explanation TEXT,
            status TEXT DEFAULT 'pending',
            librarian_action TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (book_id) REFERENCES books (book_id)
        )
        ''')

        # Schools table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            school_id TEXT PRIMARY KEY,
            school_name TEXT NOT NULL,
            district TEXT DEFAULT 'Fulton County'
        )
        ''')

        self.conn.commit()

    def generate_schools(self, num_schools=5):
        """Generate middle school data"""
        schools = []
        school_names = [
            "Woodland Middle School",
            "Riverside Middle Academy",
            "Heritage Middle School",
            "Summit View Middle School",
            "Brookstone Middle Academy"
        ]

        for i, name in enumerate(school_names[:num_schools]):
            schools.append({
                'school_id': f'MS{i+1:03d}',
                'school_name': name,
                'district': 'Fulton County'
            })

        df_schools = pd.DataFrame(schools)
        df_schools.to_sql('schools', self.conn, if_exists='replace', index=False)
        return schools

    def generate_books(self, num_books=500):
        """Generate a diverse catalog of middle-grade books"""

        # Define genres and characteristics for middle grade books
        genres = [
            'Fantasy', 'Science Fiction', 'Mystery', 'Adventure', 'Historical Fiction',
            'Contemporary Fiction', 'Biography', 'Non-fiction', 'Poetry', 'Graphic Novel'
        ]

        # Sample book templates for realistic titles
        book_templates = [
            ('The Chronicles of {place}', 'Fantasy', 'Chronicles', 6, 8),
            ('Mystery at {place}', 'Mystery', None, 5, 7),
            ('{name} and the {thing}', 'Adventure', None, 4, 6),
            ('The Secret of {thing}', 'Mystery', 'Secrets', 6, 8),
            ('Journey to {place}', 'Adventure', 'Journey', 5, 7),
            ('The Last {thing}', 'Science Fiction', None, 7, 8),
            ('Finding {name}', 'Contemporary Fiction', None, 6, 8),
            ('The {adjective} {thing}', 'Fantasy', None, 5, 7),
        ]

        authors = []
        for _ in range(100):  # Generate diverse author names
            authors.append(fake.name())

        books = []

        for i in range(num_books):
            template, genre, series, min_grade, max_grade = random.choice(book_templates)

            # Generate title using template
            if '{adjective}' in template and '{thing}' in template:
                adjs = ['Hidden', 'Ancient', 'Magical', 'Lost', 'Golden', 'Silver', 'Crystal', 'Shadow']
                things_list = ['Sword', 'Crown', 'Ring', 'Book', 'Tree', 'Island', 'City', 'Path']
                title = template.format(adjective=random.choice(adjs), thing=random.choice(things_list))
            elif '{name}' in template and '{thing}' in template:
                things_list = ['Dragon', 'Castle', 'Forest', 'Ocean', 'Mountain', 'Stone', 'Key', 'Door']
                title = template.format(name=fake.first_name(), thing=random.choice(things_list))
            elif '{place}' in template:
                title = template.format(place=fake.city())
            elif '{name}' in template:
                title = template.format(name=fake.first_name())
            elif '{thing}' in template:
                things = ['Dragon', 'Castle', 'Forest', 'Ocean', 'Mountain', 'Stone', 'Key', 'Door']
                title = template.format(thing=random.choice(things))
            else:
                title = template

            # Add series information for some books
            series_name = None
            if series and random.random() < 0.3:  # 30% chance of being in series
                series_name = series
                if random.random() < 0.7:  # 70% chance to add book number
                    title = f"{title} (Book {random.randint(1, 5)})"

            # Generate other attributes
            lexile = random.randint(400, 1200)
            pages = random.randint(150, 400)
            pub_year = random.randint(2000, 2023)

            # Generate description
            descriptions = [
                f"An exciting {genre.lower()} story that will captivate young readers.",
                f"A thrilling adventure that explores themes of friendship and courage.",
                f"A compelling tale that combines {genre.lower()} elements with coming-of-age themes.",
                f"An engaging story perfect for middle school readers who love {genre.lower()}.",
                f"A page-turner that will keep students reading late into the night."
            ]

            books.append({
                'book_id': f'BK{i+1:06d}',
                'title': title,
                'author': random.choice(authors),
                'genre': genre,
                'series': series_name,
                'grade_min': min_grade,
                'grade_max': max_grade,
                'lexile_level': lexile,
                'pages': pages,
                'publication_year': pub_year,
                'description': random.choice(descriptions),
                'isbn': f"978-{random.randint(1000000000, 9999999999)}",
                'available_copies': random.randint(1, 3)
            })

        df_books = pd.DataFrame(books)
        df_books.to_sql('books', self.conn, if_exists='replace', index=False)
        return books

    def generate_students(self, schools, students_per_school=200):
        """Generate student data across schools"""
        students = []

        reading_levels = ['Below Basic', 'Basic', 'Proficient', 'Advanced']
        level_weights = [0.15, 0.35, 0.35, 0.15]  # Realistic distribution

        for school in schools:
            for i in range(students_per_school):
                grade = random.randint(6, 8)  # Middle school grades
                reading_level = np.random.choice(reading_levels, p=level_weights)

                students.append({
                    'student_id': f"{school['school_id']}_STU{i+1:04d}",
                    'grade': grade,
                    'school_id': school['school_id'],
                    'reading_level': reading_level,
                    'created_date': fake.date_between(start_date='-3y', end_date='today')
                })

        df_students = pd.DataFrame(students)
        df_students.to_sql('students', self.conn, if_exists='replace', index=False)
        return students

    def generate_checkouts(self, students, books, num_checkouts=5000):
        """Generate realistic checkout patterns"""
        checkouts = []

        # Create student reading preferences
        student_preferences = {}
        for student in students:
            # Students tend to prefer certain genres
            preferred_genres = random.sample([b['genre'] for b in books],
                                           random.randint(1, 3))
            student_preferences[student['student_id']] = {
                'genres': preferred_genres,
                'reading_frequency': random.choice(['low', 'medium', 'high']),
                'grade': student['grade']
            }

        # Generate checkouts with realistic patterns
        checkout_id = 1
        for _ in range(num_checkouts):
            student = random.choice(students)

            # Filter books appropriate for student's grade
            appropriate_books = [
                b for b in books
                if b['grade_min'] <= student['grade'] <= b['grade_max']
            ]

            if not appropriate_books:
                continue

            # Bias towards preferred genres
            prefs = student_preferences[student['student_id']]
            if random.random() < 0.7:  # 70% chance to choose preferred genre
                genre_books = [b for b in appropriate_books if b['genre'] in prefs['genres']]
                if genre_books:
                    book = random.choice(genre_books)
                else:
                    book = random.choice(appropriate_books)
            else:
                book = random.choice(appropriate_books)

            # Generate checkout date (within last 2 years)
            checkout_date = fake.date_between(start_date='-2y', end_date='today')

            # Generate return date (typically 2-4 weeks later)
            return_date = checkout_date + timedelta(days=random.randint(7, 28))

            checkouts.append({
                'checkout_id': f'CHK{checkout_id:08d}',
                'student_id': student['student_id'],
                'book_id': book['book_id'],
                'checkout_date': checkout_date,
                'return_date': return_date,
                'school_id': student['school_id']
            })
            checkout_id += 1

        df_checkouts = pd.DataFrame(checkouts)
        df_checkouts.to_sql('checkouts', self.conn, if_exists='replace', index=False)
        return checkouts

    def generate_all_data(self):
        """Generate complete synthetic dataset"""
        print("Creating database tables...")
        self.create_tables()

        print("Generating schools...")
        schools = self.generate_schools(5)

        print("Generating books catalog...")
        books = self.generate_books(500)

        print("Generating students...")
        students = self.generate_students(schools, 200)

        print("Generating checkout history...")
        checkouts = self.generate_checkouts(students, books, 8000)

        print(f"Generated:")
        print(f"  - {len(schools)} schools")
        print(f"  - {len(books)} books")
        print(f"  - {len(students)} students")
        print(f"  - {len(checkouts)} checkouts")

        self.conn.close()
        return {
            'schools': schools,
            'books': books,
            'students': students,
            'checkouts': checkouts
        }

if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    data = generator.generate_all_data()
    print("\nSynthetic data generation complete!")