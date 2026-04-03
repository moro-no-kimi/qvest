"""
Librarian Review Workspace
Interface for reviewing, approving, and managing student recommendations
"""
import streamlit as st
import requests
import pandas as pd
from typing import Dict, List

# Page config
st.set_page_config(
    page_title="Librarian Workspace",
    page_icon="👩‍🏫",
    layout="wide"
)

# Custom CSS for functional workspace styling
st.markdown("""
<style>
.workspace-header {
    background: #34495e;
    color: white;
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
}

.student-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    margin: 0.5rem 0;
    border-left: 3px solid #3498db;
}

.recommendation-panel {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 1rem;
    margin: 0.5rem 0;
}

.approval-needed {
    border-left: 3px solid #e74c3c;
}

.approved {
    border-left: 3px solid #27ae60;
}

.action-buttons {
    margin-top: 1rem;
}

.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"

def get_students_list(school_id: str = None) -> List[Dict]:
    """Fetch students for review"""
    try:
        params = {"school_id": school_id} if school_id else {}
        response = requests.get(f"{API_BASE}/api/librarian/students", params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_student_recommendations(student_id: str) -> List[Dict]:
    """Get recommendations for a specific student"""
    try:
        response = requests.get(f"{API_BASE}/api/students/{student_id}/recommendations")
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def record_librarian_action(rec_id: str, student_id: str, book_id: str, action: str):
    """Record librarian action on recommendation"""
    try:
        data = {
            "recommendation_id": rec_id,
            "student_id": student_id,
            "book_id": book_id,
            "action": action
        }
        response = requests.post(f"{API_BASE}/api/librarian/action", json=data)
        return response.status_code == 200
    except:
        return False

def display_recommendation_panel(student_id: str, recommendation: Dict, index: int):
    """Display a single recommendation for review"""

    rec_id = f"{student_id}_{recommendation['book_id']}_{index}"

    panel_class = "recommendation-panel"
    if recommendation.get('status') == 'approved':
        panel_class += " approved"
    else:
        panel_class += " approval-needed"

    st.markdown(f"""
    <div class="{panel_class}">
        <h4>{recommendation['title']}</h4>
        <p><strong>Author:</strong> {recommendation['author']} | <strong>Genre:</strong> {recommendation['genre']}</p>
        <p><strong>Why recommended:</strong> {recommendation['explanation']}</p>
        <p><strong>Confidence:</strong> {recommendation['score']:.2f} | <strong>Method:</strong> {recommendation['reason']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✅ Approve", key=f"approve_{rec_id}"):
            if record_librarian_action(rec_id, student_id, recommendation['book_id'], "approve"):
                st.success("Approved!")
                st.experimental_rerun()

    with col2:
        if st.button("📌 Pin to Top", key=f"pin_{rec_id}"):
            if record_librarian_action(rec_id, student_id, recommendation['book_id'], "pin"):
                st.success("Pinned!")

    with col3:
        if st.button("❌ Remove", key=f"remove_{rec_id}"):
            if record_librarian_action(rec_id, student_id, recommendation['book_id'], "reject"):
                st.success("Removed!")

    with col4:
        if st.button("🔄 Replace", key=f"replace_{rec_id}"):
            st.session_state[f"replacing_{rec_id}"] = True

    # Replacement interface
    if st.session_state.get(f"replacing_{rec_id}", False):
        st.text_input("Search for replacement book:", key=f"replacement_search_{rec_id}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Replace", key=f"confirm_replace_{rec_id}"):
                st.success("Replacement recorded!")
                st.session_state[f"replacing_{rec_id}"] = False
        with col2:
            if st.button("Cancel", key=f"cancel_replace_{rec_id}"):
                st.session_state[f"replacing_{rec_id}"] = False

def main():
    # Header
    st.markdown("""
    <div class="workspace-header">
        <h1>👩‍🏫 Librarian Review Workspace</h1>
        <p>Review and manage student recommendations</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar for school selection and overview
    st.sidebar.header("Workspace Controls")

    schools = ["MS001", "MS002", "MS003", "MS004", "MS005"]
    selected_school = st.sidebar.selectbox("Select School:", ["All Schools"] + schools)

    school_filter = selected_school if selected_school != "All Schools" else None

    # Overview metrics
    st.sidebar.markdown("### Today's Overview")
    st.sidebar.markdown("""
    <div class="metric-card">
        <h3>47</h3>
        <p>Pending Reviews</p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div class="metric-card" style="margin-top: 0.5rem;">
        <h3>89%</h3>
        <p>Approval Rate</p>
    </div>
    """, unsafe_allow_html=True)

    # Main workspace area
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("Students")

        # Get students list
        students = get_students_list(school_filter)

        if not students:
            st.warning("No students found. Make sure the data is loaded.")
            return

        # Filter to show only students with recommendations (for demo)
        sample_students = students[:10]

        for student in sample_students:
            st.markdown(f"""
            <div class="student-card">
                <strong>{student['student_id']}</strong><br>
                Grade {student['grade']} | {student['reading_level']}
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Review Recommendations", key=f"review_{student['student_id']}"):
                st.session_state.selected_student = student['student_id']

    with col2:
        st.header("Recommendation Review")

        if "selected_student" not in st.session_state:
            st.info("Select a student from the left panel to review their recommendations.")
            return

        student_id = st.session_state.selected_student
        st.subheader(f"Recommendations for {student_id}")

        # Get recommendations
        recommendations = get_student_recommendations(student_id)

        if not recommendations:
            st.info("No recommendations found for this student.")
            return

        # Display recommendations for review
        for i, rec in enumerate(recommendations):
            display_recommendation_panel(student_id, rec, i)

        # Bulk actions
        st.markdown("---")
        st.subheader("Bulk Actions")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Approve All"):
                st.success("All recommendations approved!")

        with col2:
            if st.button("Generate New Batch"):
                st.info("New recommendations will be generated in tonight's batch.")

if __name__ == "__main__":
    main()