"""
Student Recommendation Interface
Simple, warm interface showing personalized book recommendations
"""
import streamlit as st
import requests
import pandas as pd
from typing import Dict, List

# Page config
st.set_page_config(
    page_title="Your Reading Recommendations",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for library-like styling
st.markdown("""
<style>
.main-header {
    font-family: 'Georgia', serif;
    color: #2c3e50;
    text-align: center;
    margin-bottom: 2rem;
}

.book-card {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid #3498db;
    margin: 1rem 0;
}

.book-title {
    font-family: 'Georgia', serif;
    font-size: 1.4rem;
    color: #2c3e50;
    margin-bottom: 0.5rem;
}

.book-author {
    color: #7f8c8d;
    font-style: italic;
    margin-bottom: 0.5rem;
}

.explanation {
    background: #e8f6f3;
    padding: 1rem;
    border-radius: 4px;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}

.secondary-recs {
    margin-top: 2rem;
}

.interested-btn {
    background-color: #27ae60;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"

def get_student_recommendations(student_id: str) -> List[Dict]:
    """Fetch recommendations from API"""
    try:
        response = requests.get(f"{API_BASE}/api/students/{student_id}/recommendations")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching recommendations: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Could not connect to recommendation service: {e}")
        return []

def display_book_recommendation(book: Dict, is_primary: bool = False):
    """Display a single book recommendation"""
    card_class = "book-card primary" if is_primary else "book-card"

    st.markdown(f"""
    <div class="{card_class}">
        <div class="book-title">{book['title']}</div>
        <div class="book-author">by {book['author']}</div>
        <div class="explanation">
            📖 {book['explanation']}
        </div>
        <p><strong>Genre:</strong> {book['genre']}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button(f"I'm Interested", key=f"interest_{book['book_id']}"):
            st.success("Saved to your list! Ask your librarian where to find this book.")
    with col2:
        st.text("Available in the library")

def main():
    # Header
    st.markdown('<h1 class="main-header">📚 Your Reading Recommendations</h1>', unsafe_allow_html=True)

    # Demo student selector
    st.sidebar.header("Demo Student Login")
    sample_students = [
        "MS001_STU0001",
        "MS001_STU0050",
        "MS001_STU0100",
        "MS002_STU0001",
        "MS002_STU0050"
    ]

    selected_student = st.sidebar.selectbox(
        "Select a demo student:",
        sample_students,
        help="In production, this would be automatic from ClassLink SSO"
    )

    if st.sidebar.button("Get My Recommendations"):
        st.session_state.student_id = selected_student

    # Main content
    if "student_id" not in st.session_state:
        st.info("👋 Welcome! Click 'Get My Recommendations' in the sidebar to see books picked just for you.")
        return

    student_id = st.session_state.student_id

    # Fetch recommendations
    with st.spinner("Finding your next great books..."):
        recommendations = get_student_recommendations(student_id)

    if not recommendations:
        st.warning("We don't have personalized picks for you yet. Try again after tomorrow's refresh or ask your librarian for suggestions!")
        return

    # Display primary recommendation
    if recommendations:
        st.markdown("### Your Top Pick")
        display_book_recommendation(recommendations[0], is_primary=True)

    # Display secondary recommendations
    if len(recommendations) > 1:
        st.markdown('<div class="secondary-recs">', unsafe_allow_html=True)
        st.markdown("### More Books You Might Enjoy")

        for book in recommendations[1:]:
            display_book_recommendation(book)

        st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #7f8c8d; font-size: 0.9rem;'>
        Questions? Ask your librarian! 📚
        <br>
        <em>Recommendations update nightly</em>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()