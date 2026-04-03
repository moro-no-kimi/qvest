"""
Setup script for Fulton County Reading Lift Pilot Proof of Concept
Generates synthetic data and trains recommendation models
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from data.synthetic_data_generator import SyntheticDataGenerator
from models.recommendation_engine import HybridRecommendationEngine

def setup_directories():
    """Create necessary directories"""
    directories = ['data', 'models', 'api', 'ui', 'logs']
    for dir_name in directories:
        os.makedirs(dir_name, exist_ok=True)
    print("✅ Directories created")

def generate_synthetic_data():
    """Generate synthetic library data"""
    print("📚 Generating synthetic library data...")

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Generate data
    generator = SyntheticDataGenerator("data/library_data.db")
    data = generator.generate_all_data()

    print(f"✅ Generated synthetic data:")
    print(f"   - {len(data['schools'])} schools")
    print(f"   - {len(data['books'])} books")
    print(f"   - {len(data['students'])} students")
    print(f"   - {len(data['checkouts'])} checkouts")

def generate_sample_recommendations():
    """Generate sample recommendations for demo"""
    print("🔮 Generating sample recommendations...")

    engine = HybridRecommendationEngine("data/library_data.db")
    engine.fit()

    # Generate recommendations for a few sample students
    conn = sqlite3.connect("data/library_data.db")
    cursor = conn.cursor()

    # Get sample students
    students_df = engine.students_df.head(20)

    recommendation_id = 1
    for _, student in students_df.iterrows():
        try:
            recommendations = engine.generate_recommendations(student['student_id'], n_recommendations=5)

            for rec in recommendations:
                cursor.execute("""
                INSERT INTO recommendations
                (recommendation_id, student_id, book_id, recommendation_score, reason, explanation, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"REC{recommendation_id:06d}",
                    student['student_id'],
                    rec['book_id'],
                    rec['score'],
                    rec['reason'],
                    rec['explanation'],
                    'pending'
                ])
                recommendation_id += 1

        except Exception as e:
            print(f"   Warning: Could not generate recommendations for {student['student_id']}: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"✅ Generated {recommendation_id-1} sample recommendations")

def verify_setup():
    """Verify that setup completed successfully"""
    print("🔍 Verifying setup...")

    # Check database exists and has data
    db_path = "data/library_data.db"
    if not os.path.exists(db_path):
        print("❌ Database not found")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables exist and have data
    tables = ['books', 'students', 'checkouts', 'schools', 'recommendations']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count == 0:
            print(f"❌ Table {table} is empty")
            conn.close()
            return False
        else:
            print(f"   ✅ {table}: {count} records")

    conn.close()
    return True

def main():
    """Main setup process"""
    print("🚀 Setting up Fulton County Reading Lift Pilot Proof of Concept")
    print("=" * 60)

    try:
        # Create directories
        setup_directories()

        # Generate synthetic data
        generate_synthetic_data()

        # Generate sample recommendations
        generate_sample_recommendations()

        # Verify setup
        if verify_setup():
            print("=" * 60)
            print("✅ Setup completed successfully!")
            print("\nNext steps:")
            print("1. Install requirements: pip install -r requirements.txt")
            print("2. Start API server: python api/main.py")
            print("3. Run student app: streamlit run ui/student_app.py")
            print("4. Run librarian app: streamlit run ui/librarian_app.py")
            print("5. Run dashboard: streamlit run ui/district_dashboard.py")
        else:
            print("❌ Setup verification failed")
            return 1

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())