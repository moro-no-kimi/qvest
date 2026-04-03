#!/usr/bin/env python3
"""
Streamlit librarian review workspace.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(__file__))

from data_pipeline import DataPipeline
from hybrid_recommender import HybridRecommender, RecommendationConfig
from explanation_generator import LLMExplanationGenerator


def load_data():
    """Load and cache data."""
    if 'librarian_data_loaded' not in st.session_state:
        with st.spinner('Loading system data...'):
            pipeline = DataPipeline()
            books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

            config = RecommendationConfig()
            recommender = HybridRecommender(config)
            recommender.fit(books_df, students_df, pipeline.interaction_matrix)

            explainer = LLMExplanationGenerator(use_mock_llm=True)

            st.session_state.librarian_data_loaded = True
            st.session_state.lib_books_df = books_df
            st.session_state.lib_students_df = students_df
            st.session_state.lib_checkouts_df = checkouts_df
            st.session_state.lib_recommender = recommender
            st.session_state.lib_explainer = explainer

    return (st.session_state.lib_books_df, st.session_state.lib_students_df,
            st.session_state.lib_checkouts_df, st.session_state.lib_recommender,
            st.session_state.lib_explainer)


def display_recommendation_review(rec: Dict, student_info: pd.Series, book_info: pd.Series):
    """Display recommendation for librarian review."""

    # Status indicator
    status = "🟡 NEEDS REVIEW" if rec.get('requires_review', False) else "✅ AUTO-APPROVED"
    confidence = rec.get('confidence', 0.0)

    st.markdown(f"**Status:** {status} | **Confidence:** {confidence:.2f}")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(f"**Book:** {rec['title']} by {rec['author']}")
        st.write(f"**Genre:** {rec['genre']} | **Reading Level:** {book_info['reading_level']}L")
        st.write(f"**Description:** {book_info['description'][:150]}...")

        # Explanation
        explanation = rec.get('explanation', 'No explanation available')
        st.info(f"💡 **AI Explanation:** {explanation}")

        # Policy violations if any
        violations = rec.get('policy_violations', [])
        if violations:
            st.warning(f"⚠️ **Policy Notes:** {', '.join(violations)}")

    with col2:
        st.metric("Pages", book_info['pages'])
        st.metric("Popularity", f"{book_info['checkout_count']} checkouts")
        st.metric("Available", f"{book_info['copies_available']} copies")

    # Action buttons
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("✅ Approve", key=f"approve_{rec['book_id']}"):
            st.success("Recommendation approved!")
            return "approved"

    with col_btn2:
        if st.button("📌 Pin to Top", key=f"pin_{rec['book_id']}"):
            st.success("Pinned as top recommendation!")
            return "pinned"

    with col_btn3:
        if st.button("✏️ Replace", key=f"replace_{rec['book_id']}"):
            st.info("Replacement mode activated")
            return "replace"

    with col_btn4:
        if st.button("❌ Suppress", key=f"suppress_{rec['book_id']}"):
            st.warning("Recommendation suppressed")
            return "suppressed"

    return None


def librarian_workspace():
    """Main librarian workspace."""
    st.set_page_config(
        page_title="Librarian Review Workspace",
        page_icon="👩‍🏫",
        layout="wide"
    )

    st.title("👩‍🏫 Librarian Review Workspace")
    st.markdown("*Review and manage AI-generated book recommendations*")

    # Load data
    books_df, students_df, checkouts_df, recommender, explainer = load_data()

    # Sidebar controls
    st.sidebar.header("🔍 Search & Filter")

    # School filter
    schools = students_df['school'].unique()
    selected_school = st.sidebar.selectbox("Select School:", ['All Schools'] + list(schools))

    # Filter students by school
    if selected_school != 'All Schools':
        filtered_students = students_df[students_df['school'] == selected_school]
    else:
        filtered_students = students_df

    # Student search
    search_term = st.sidebar.text_input("Search Student ID:")

    if search_term:
        filtered_students = filtered_students[
            filtered_students['student_id'].str.contains(search_term, case=False)
        ]

    # Grade filter
    grades = sorted(filtered_students['grade'].unique())
    selected_grades = st.sidebar.multiselect("Filter by Grade:", grades, default=grades)
    filtered_students = filtered_students[filtered_students['grade'].isin(selected_grades)]

    # Review status filter
    review_filter = st.sidebar.radio(
        "Show Recommendations:",
        ["All", "Needs Review Only", "Auto-Approved Only"]
    )

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📋 Review Queue", "👥 Student Lookup", "📊 Review Statistics"])

    with tab1:
        st.header("📋 Recommendation Review Queue")

        # Quick stats
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        with col_stat1:
            st.metric("Students in Queue", len(filtered_students))

        with col_stat2:
            st.metric("School(s)", selected_school if selected_school != 'All Schools' else len(schools))

        with col_stat3:
            total_checkouts = filtered_students['total_checkouts'].sum()
            st.metric("Total Checkouts", total_checkouts)

        with col_stat4:
            avg_checkouts = filtered_students['total_checkouts'].mean()
            st.metric("Avg per Student", f"{avg_checkouts:.1f}")

        # Process recommendations for review
        st.subheader("⏳ Processing Recommendations...")

        # Show a sample of students who need review
        sample_students = filtered_students.head(5)  # Limit for demo

        for _, student in sample_students.iterrows():
            with st.expander(f"📚 {student['student_id']} (Grade {student['grade']}) - {student['school']}", expanded=False):

                # Student summary
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Reading Profile:** {student['reading_profile']}")
                    st.write(f"**Total Checkouts:** {student['total_checkouts']}")
                    st.write(f"**Favorite Genre:** {student['favorite_genre']}")

                with col_info2:
                    st.write(f"**Genres Explored:** {student['unique_genres']}")
                    st.write(f"**Avg Book Length:** {student['avg_book_length']:.0f} pages")

                # Get recommendations for this student
                try:
                    recommendations = recommender.recommend_for_user(student['student_id'], n_recommendations=3)

                    if recommendations:
                        needs_review_count = sum(1 for r in recommendations if r.get('requires_review', False))
                        st.write(f"**Recommendations:** {len(recommendations)} generated, {needs_review_count} need review")

                        # Show recommendations based on filter
                        for i, rec in enumerate(recommendations):
                            requires_review = rec.get('requires_review', False)

                            # Apply review filter
                            if review_filter == "Needs Review Only" and not requires_review:
                                continue
                            elif review_filter == "Auto-Approved Only" and requires_review:
                                continue

                            book_info = books_df[books_df['book_id'] == rec['book_id']].iloc[0]

                            with st.container():
                                st.markdown("---")
                                st.write(f"**Recommendation {i+1}:**")

                                action = display_recommendation_review(rec, student, book_info)

                                if action:
                                    # Log the action (in real system, this would update database)
                                    st.session_state[f"action_{student['student_id']}_{rec['book_id']}"] = action
                    else:
                        st.info("No recommendations generated for this student yet.")

                except Exception as e:
                    st.error(f"Error generating recommendations: {str(e)}")

    with tab2:
        st.header("👥 Student Lookup")

        # Student selector
        student_options = filtered_students['student_id'].tolist()
        if student_options:
            selected_student = st.selectbox("Select Student:", student_options)

            if selected_student:
                student_data = students_df[students_df['student_id'] == selected_student].iloc[0]

                # Student profile
                col_profile1, col_profile2 = st.columns(2)

                with col_profile1:
                    st.subheader("📋 Student Profile")
                    st.write(f"**ID:** {student_data['student_id']}")
                    st.write(f"**Grade:** {student_data['grade']}")
                    st.write(f"**School:** {student_data['school']}")
                    st.write(f"**Reading Profile:** {student_data['reading_profile']}")

                with col_profile2:
                    st.subheader("📊 Reading Statistics")
                    st.metric("Books Read", student_data['total_checkouts'])
                    st.metric("Genres", student_data['unique_genres'])
                    st.metric("Favorite Genre", student_data['favorite_genre'])

                # Recent reading history
                st.subheader("📖 Recent Reading History")
                recent_checkouts = checkouts_df[checkouts_df['student_id'] == selected_student].tail(5)

                if len(recent_checkouts) > 0:
                    history_data = []
                    for _, checkout in recent_checkouts.iterrows():
                        book_info = books_df[books_df['book_id'] == checkout['book_id']].iloc[0]
                        history_data.append({
                            'Date': checkout['checkout_date'],
                            'Title': book_info['title'],
                            'Author': book_info['author'],
                            'Genre': book_info['genre']
                        })

                    st.dataframe(pd.DataFrame(history_data))
                else:
                    st.info("No reading history found.")

                # Generate fresh recommendations
                if st.button("🎯 Generate New Recommendations"):
                    with st.spinner("Generating recommendations..."):
                        recommendations = recommender.recommend_for_user(selected_student, n_recommendations=5)

                        st.subheader("💡 Fresh Recommendations")
                        for i, rec in enumerate(recommendations, 1):
                            book_info = books_df[books_df['book_id'] == rec['book_id']].iloc[0]

                            with st.expander(f"{i}. {rec['title']}", expanded=False):
                                display_recommendation_review(rec, student_data, book_info)
        else:
            st.info("No students match your current filters.")

    with tab3:
        st.header("📊 Review Statistics")

        # System-wide stats
        col_sys1, col_sys2, col_sys3 = st.columns(3)

        with col_sys1:
            st.metric("Total Students", len(students_df))
            st.metric("Total Books", len(books_df))

        with col_sys2:
            st.metric("Active Schools", students_df['school'].nunique())
            st.metric("Total Checkouts", len(checkouts_df))

        with col_sys3:
            available_books = books_df[books_df['copies_available'] > 0]['book_id'].nunique()
            availability_rate = available_books / len(books_df)
            st.metric("Book Availability", f"{availability_rate:.1%}")

        # Reading profile breakdown
        st.subheader("📈 Student Reading Profiles")
        profile_counts = students_df['reading_profile'].value_counts()
        st.bar_chart(profile_counts)

        # Genre popularity
        st.subheader("📚 Popular Genres")
        genre_checkouts = checkouts_df.merge(books_df[['book_id', 'genre']], on='book_id')
        genre_popularity = genre_checkouts['genre'].value_counts().head(10)
        st.bar_chart(genre_popularity)

        # Mock review statistics
        st.subheader("⚖️ Review Activity (Mock Data)")
        review_stats = pd.DataFrame({
            'Action': ['Auto-Approved', 'Manually Approved', 'Pinned', 'Replaced', 'Suppressed'],
            'Count': [145, 32, 18, 12, 8],
            'Percentage': [67.4, 14.9, 8.4, 5.6, 3.7]
        })

        col_review1, col_review2 = st.columns(2)
        with col_review1:
            st.dataframe(review_stats)
        with col_review2:
            st.bar_chart(review_stats.set_index('Action')['Count'])


def main():
    """Run the librarian workspace."""
    librarian_workspace()


if __name__ == "__main__":
    main()