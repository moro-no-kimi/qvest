"""
FastAPI backend for Fulton County Reading Lift Pilot
Provides endpoints for students, librarians, and district administrators
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import sqlite3
import pandas as pd
from datetime import datetime
import sys
import os

# Add models directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.recommendation_engine import HybridRecommendationEngine

app = FastAPI(title="Reading Lift Pilot API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize recommendation engine
engine = HybridRecommendationEngine()

# Pydantic models
class Recommendation(BaseModel):
    book_id: str
    title: str
    author: str
    genre: str
    score: float
    reason: str
    explanation: str
    status: str

class LibrarianAction(BaseModel):
    recommendation_id: str
    student_id: str
    book_id: str
    action: str  # 'approve', 'reject', 'pin', 'replace'
    replacement_book_id: Optional[str] = None
    notes: Optional[str] = None

# Database connection
def get_db_connection():
    return sqlite3.connect("data/library_data.db")

@app.on_event("startup")
async def startup_event():
    """Initialize the recommendation engine on startup"""
    try:
        engine.fit()
        print("Recommendation engine initialized successfully")
    except Exception as e:
        print(f"Error initializing recommendation engine: {e}")

# Student endpoints
@app.get("/api/students/{student_id}/recommendations", response_model=List[Recommendation])
async def get_student_recommendations(student_id: str):
    """Get personalized recommendations for a student"""
    try:
        recommendations = engine.generate_recommendations(student_id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@app.get("/api/students/{student_id}/profile")
async def get_student_profile(student_id: str):
    """Get student profile information"""
    conn = get_db_connection()
    try:
        # Get student info
        student_query = "SELECT * FROM students WHERE student_id = ?"
        student_df = pd.read_sql_query(student_query, conn, params=[student_id])

        if student_df.empty:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get recent checkouts
        checkouts_query = """
        SELECT c.*, b.title, b.author, b.genre
        FROM checkouts c
        JOIN books b ON c.book_id = b.book_id
        WHERE c.student_id = ?
        ORDER BY c.checkout_date DESC
        LIMIT 5
        """
        checkouts_df = pd.read_sql_query(checkouts_query, conn, params=[student_id])

        return {
            "student": student_df.to_dict(orient="records")[0],
            "recent_books": checkouts_df.to_dict(orient="records")
        }
    finally:
        conn.close()

# Librarian endpoints
@app.get("/api/librarian/students")
async def get_students_for_librarian(school_id: Optional[str] = None):
    """Get list of students for librarian review"""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM students"
        params = []

        if school_id:
            query += " WHERE school_id = ?"
            params.append(school_id)

        students_df = pd.read_sql_query(query, conn, params=params)
        return students_df.to_dict(orient="records")
    finally:
        conn.close()

@app.post("/api/librarian/action")
async def librarian_action(action: LibrarianAction):
    """Record librarian action on a recommendation"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Update recommendation status
        new_status = "approved" if action.action == "approve" else "modified"

        cursor.execute("""
        UPDATE recommendations
        SET status = ?, librarian_action = ?
        WHERE recommendation_id = ?
        """, [new_status, action.action, action.recommendation_id])

        conn.commit()
        return {"success": True, "message": "Action recorded successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording action: {str(e)}")
    finally:
        conn.close()

# District dashboard endpoints
@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """Get district-level metrics for the pilot"""
    conn = get_db_connection()
    try:
        # Overall metrics
        total_students = pd.read_sql_query("SELECT COUNT(*) as count FROM students", conn).iloc[0]['count']
        total_books = pd.read_sql_query("SELECT COUNT(*) as count FROM books", conn).iloc[0]['count']
        total_checkouts = pd.read_sql_query("SELECT COUNT(*) as count FROM checkouts", conn).iloc[0]['count']

        # Mock recommendation metrics for demo
        rec_metrics = {
            'total_recommendations': 1500,
            'approved_recommendations': 1200,
            'librarian_approved': 800,
            'librarian_replaced': 200
        }

        # School-level metrics
        schools_df = pd.read_sql_query("SELECT * FROM schools", conn)
        school_metrics = []
        for _, school in schools_df.iterrows():
            school_students = pd.read_sql_query(
                "SELECT COUNT(*) as count FROM students WHERE school_id = ?",
                conn, params=[school['school_id']]
            ).iloc[0]['count']

            school_metrics.append({
                'school_id': school['school_id'],
                'school_name': school['school_name'],
                'total_students': school_students,
                'recommendations_generated': int(school_students * 0.8),
                'recommendations_approved': int(school_students * 0.6)
            })

        return {
            "overview": {
                "total_students": total_students,
                "total_books": total_books,
                "total_checkouts": total_checkouts,
                **rec_metrics
            },
            "schools": school_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)