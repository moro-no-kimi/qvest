#!/usr/bin/env python3
"""
FastAPI backend for the Reading Lift Pilot recommendation system.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import uvicorn
import os

from data_pipeline import DataPipeline
from hybrid_recommender import HybridRecommender, RecommendationConfig
from explanation_generator import LLMExplanationGenerator


# Pydantic models for API requests/responses
class StudentInfo(BaseModel):
    student_id: str
    grade: int
    school: str
    reading_profile: str
    total_checkouts: int
    favorite_genre: str


class BookInfo(BaseModel):
    book_id: str
    title: str
    author: str
    genre: str
    reading_level: int
    pages: int
    description: str
    is_series: bool
    series_name: Optional[str] = None
    checkout_count: int
    copies_available: int


class Recommendation(BaseModel):
    book_id: str
    title: str
    author: str
    genre: str
    confidence: float
    explanation: str
    sources: List[str]
    requires_review: bool
    policy_violations: List[str]


class RecommendationRequest(BaseModel):
    student_id: str
    n_recommendations: Optional[int] = 10


class SystemStats(BaseModel):
    status: str
    students: int
    books: int
    available_books: int
    availability_rate: float


# Global variables for loaded models and data
app_data = {
    'pipeline': None,
    'recommender': None,
    'explainer': None,
    'books_df': None,
    'students_df': None,
    'checkouts_df': None,
    'is_loaded': False
}


# FastAPI app
app = FastAPI(
    title="Reading Lift Pilot API",
    description="AI-powered book recommendation system for Fulton County Schools",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Load data and train models on startup."""
    print("🚀 Starting Reading Lift Pilot API...")

    try:
        # Load and process data
        print("📥 Loading data...")
        pipeline = DataPipeline()
        books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

        # Initialize recommendation system
        print("🎯 Training recommendation models...")
        config = RecommendationConfig(
            collab_weight=0.4,
            content_weight=0.4,
            popularity_weight=0.2
        )
        recommender = HybridRecommender(config)
        recommender.fit(books_df, students_df, pipeline.interaction_matrix)

        # Initialize explanation generator
        explainer = LLMExplanationGenerator(use_mock_llm=True)

        # Store in global state
        app_data.update({
            'pipeline': pipeline,
            'recommender': recommender,
            'explainer': explainer,
            'books_df': books_df,
            'students_df': students_df,
            'checkouts_df': checkouts_df,
            'is_loaded': True
        })

        print("✅ API ready!")

    except Exception as e:
        print(f"❌ Failed to initialize API: {e}")
        raise


@app.get("/")
async def root():
    """API health check."""
    return {
        "message": "Reading Lift Pilot API",
        "status": "running" if app_data['is_loaded'] else "loading",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    stats = app_data['recommender'].get_system_stats()
    return {
        "status": "healthy",
        "loaded": True,
        "students": stats.get('students', 0),
        "books": stats.get('books', 0),
        "models_trained": True
    }


@app.get("/students", response_model=List[StudentInfo])
async def get_students():
    """Get list of all students."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    students = []
    for _, student in app_data['students_df'].iterrows():
        students.append(StudentInfo(
            student_id=student['student_id'],
            grade=int(student['grade']),
            school=student['school'],
            reading_profile=student['reading_profile'],
            total_checkouts=int(student['total_checkouts']),
            favorite_genre=student['favorite_genre']
        ))

    return students


@app.get("/students/{student_id}", response_model=StudentInfo)
async def get_student(student_id: str):
    """Get specific student information."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    student_data = app_data['students_df'][app_data['students_df']['student_id'] == student_id]

    if len(student_data) == 0:
        raise HTTPException(status_code=404, detail="Student not found")

    student = student_data.iloc[0]
    return StudentInfo(
        student_id=student['student_id'],
        grade=int(student['grade']),
        school=student['school'],
        reading_profile=student['reading_profile'],
        total_checkouts=int(student['total_checkouts']),
        favorite_genre=student['favorite_genre']
    )


@app.get("/books", response_model=List[BookInfo])
async def get_books(limit: int = 50):
    """Get list of books (with optional limit)."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    books = []
    for _, book in app_data['books_df'].head(limit).iterrows():
        books.append(BookInfo(
            book_id=book['book_id'],
            title=book['title'],
            author=book['author'],
            genre=book['genre'],
            reading_level=int(book['reading_level']),
            pages=int(book['pages']),
            description=book['description'],
            is_series=bool(book['is_series']),
            series_name=book.get('series_name'),
            checkout_count=int(book['checkout_count']),
            copies_available=int(book['copies_available'])
        ))

    return books


@app.get("/books/{book_id}", response_model=BookInfo)
async def get_book(book_id: str):
    """Get specific book information."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    book_data = app_data['books_df'][app_data['books_df']['book_id'] == book_id]

    if len(book_data) == 0:
        raise HTTPException(status_code=404, detail="Book not found")

    book = book_data.iloc[0]
    return BookInfo(
        book_id=book['book_id'],
        title=book['title'],
        author=book['author'],
        genre=book['genre'],
        reading_level=int(book['reading_level']),
        pages=int(book['pages']),
        description=book['description'],
        is_series=bool(book['is_series']),
        series_name=book.get('series_name'),
        checkout_count=int(book['checkout_count']),
        copies_available=int(book['copies_available'])
    )


@app.post("/recommendations", response_model=List[Recommendation])
async def get_recommendations(request: RecommendationRequest):
    """Get book recommendations for a student."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    try:
        # Get student info
        student_data = app_data['students_df'][app_data['students_df']['student_id'] == request.student_id]
        if len(student_data) == 0:
            raise HTTPException(status_code=404, detail="Student not found")

        student = student_data.iloc[0]

        # Get recommendations from hybrid system
        raw_recommendations = app_data['recommender'].recommend_for_user(
            request.student_id,
            n_recommendations=request.n_recommendations
        )

        # Get student reading history for explanations
        student_checkouts = app_data['checkouts_df'][
            app_data['checkouts_df']['student_id'] == request.student_id
        ]['book_id'].tolist()

        reading_history = []
        for book_id in student_checkouts[:5]:  # Recent 5 books
            book_info = app_data['books_df'][app_data['books_df']['book_id'] == book_id]
            if len(book_info) > 0:
                book = book_info.iloc[0]
                reading_history.append({
                    'title': book['title'],
                    'author': book['author'],
                    'genre': book['genre']
                })

        # Generate enhanced explanations
        enhanced_recommendations = app_data['explainer'].generate_batch_explanations(
            raw_recommendations,
            int(student['grade']),
            reading_history
        )

        # Convert to API response format
        recommendations = []
        for rec in enhanced_recommendations:
            recommendations.append(Recommendation(
                book_id=rec['book_id'],
                title=rec['title'],
                author=rec['author'],
                genre=rec['genre'],
                confidence=rec['confidence'],
                explanation=rec['explanation'],
                sources=rec.get('sources', []),
                requires_review=rec.get('requires_review', False),
                policy_violations=rec.get('policy_violations', [])
            ))

        return recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@app.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """Get system statistics."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    stats = app_data['recommender'].get_system_stats()
    return SystemStats(
        status=stats['status'],
        students=stats['students'],
        books=stats['books'],
        available_books=stats['available_books'],
        availability_rate=stats['availability_rate']
    )


@app.get("/popular-books")
async def get_popular_books(limit: int = 10):
    """Get most popular books."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    popular = app_data['books_df'].nlargest(limit, 'checkout_count')[
        ['book_id', 'title', 'author', 'genre', 'checkout_count']
    ].to_dict('records')

    return {"popular_books": popular}


@app.get("/school-stats/{school_name}")
async def get_school_stats(school_name: str):
    """Get statistics for a specific school."""
    if not app_data['is_loaded']:
        raise HTTPException(status_code=503, detail="System still loading")

    # Filter data for the school
    school_students = app_data['students_df'][app_data['students_df']['school'] == school_name]
    school_checkouts = app_data['checkouts_df'][app_data['checkouts_df']['school'] == school_name]

    if len(school_students) == 0:
        raise HTTPException(status_code=404, detail="School not found")

    stats = {
        "school_name": school_name,
        "total_students": len(school_students),
        "total_checkouts": len(school_checkouts),
        "avg_checkouts_per_student": school_students['total_checkouts'].mean(),
        "grade_breakdown": school_students['grade'].value_counts().to_dict(),
        "reading_profiles": school_students['reading_profile'].value_counts().to_dict()
    }

    return stats


def main():
    """Run the API server."""
    print("🚀 Starting Reading Lift Pilot API server...")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()