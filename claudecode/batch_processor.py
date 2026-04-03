"""
Nightly Batch Processor for Reading Lift Pilot
Simulates the daily recommendation generation pipeline
"""
import sys
import os
from datetime import datetime
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from models.recommendation_engine import HybridRecommendationEngine

def log_message(message: str):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def clear_old_recommendations():
    """Clear previous day's recommendations"""
    conn = sqlite3.connect("data/library_data.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM recommendations WHERE status = 'pending'")
    cleared = cursor.rowcount
    conn.commit()
    conn.close()

    log_message(f"Cleared {cleared} pending recommendations from previous run")

def generate_nightly_recommendations():
    """Generate fresh recommendations for all active students"""
    log_message("Initializing recommendation engine...")

    engine = HybridRecommendationEngine("data/library_data.db")
    engine.fit()

    # Get subset of students for demo
    students_df = engine.students_df.head(50)  # Process 50 students for demo

    # Connect to database
    conn = sqlite3.connect("data/library_data.db")
    cursor = conn.cursor()

    recommendations_generated = 0
    students_processed = 0

    log_message(f"Processing {len(students_df)} students...")

    for _, student in students_df.iterrows():
        try:
            student_id = student['student_id']

            # Generate recommendations
            recommendations = engine.generate_recommendations(student_id, n_recommendations=5)

            # Store recommendations
            for i, rec in enumerate(recommendations):
                rec_id = f"{student_id}_REC_{datetime.now().strftime('%Y%m%d')}_{i+1}"

                cursor.execute("""
                INSERT OR REPLACE INTO recommendations
                (recommendation_id, student_id, book_id, recommendation_score, reason, explanation, status, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    rec_id,
                    student_id,
                    rec['book_id'],
                    rec['score'],
                    rec['reason'],
                    rec['explanation'],
                    'pending',
                    datetime.now().isoformat()
                ])

                recommendations_generated += 1

            students_processed += 1

        except Exception as e:
            log_message(f"Error processing student {student['student_id']}: {e}")
            continue

    # Commit all changes
    conn.commit()
    conn.close()

    log_message(f"Batch processing complete:")
    log_message(f"  - Students processed: {students_processed}")
    log_message(f"  - Recommendations generated: {recommendations_generated}")

def main():
    """Main batch processing pipeline"""
    log_message("=" * 60)
    log_message("Starting nightly recommendation batch process")
    log_message("=" * 60)

    try:
        # Check database exists
        if not os.path.exists("data/library_data.db"):
            log_message("❌ Database not found. Please run setup.py first.")
            return 1

        # Step 1: Clear old recommendations
        clear_old_recommendations()

        # Step 2: Generate new recommendations
        generate_nightly_recommendations()

        log_message("=" * 60)
        log_message("✅ Batch processing completed successfully")
        log_message("=" * 60)

    except Exception as e:
        log_message(f"❌ Batch processing failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())