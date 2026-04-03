#!/usr/bin/env python3
"""
Streamlit student recommendation page.
"""

import streamlit as st
import pandas as pd
import requests
from typing import List, Dict
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.dirname(__file__))

from data_pipeline import DataPipeline
from hybrid_recommender import HybridRecommender, RecommendationConfig
from explanation_generator import LLMExplanationGenerator


def load_data():
    """Load and cache data."""
    if 'data_loaded' not in st.session_state:
        with st.spinner('Loading library data...'):
            pipeline = DataPipeline()
            books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

            # Train models
            config = RecommendationConfig(collab_weight=0.4, content_weight=0.4, popularity_weight=0.2)
            recommender = HybridRecommender(config)
            recommender.fit(books_df, students_df, pipeline.interaction_matrix)

            explainer = LLMExplanationGenerator(use_mock_llm=True)

            st.session_state.data_loaded = True
            st.session_state.books_df = books_df
            st.session_state.students_df = students_df
            st.session_state.checkouts_df = checkouts_df
            st.session_state.recommender = recommender
            st.session_state.explainer = explainer

    return (st.session_state.books_df, st.session_state.students_df,
            st.session_state.checkouts_df, st.session_state.recommender,
            st.session_state.explainer)


def display_book_card(book_info: Dict, explanation: str = "", show_explanation: bool = True):
    """Display a book recommendation card."""
    with st.container():
        st.markdown("---")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"📚 {book_info['title']}")
            st.write(f"**by {book_info['author']}**")
            st.write(f"*Genre:* {book_info['genre']}")

            if show_explanation and explanation:
                st.info(f"💡 {explanation}")

        with col2:
            st.metric("Reading Level", f"{book_info.get('reading_level', 800)}L")
            st.metric("Pages", book_info.get('pages', 200))

            availability = book_info.get('copies_available', 1)
            if availability > 0:
                st.success(f"✅ {availability} copies available")
            else:
                st.error("❌ Currently unavailable")


def student_page():
    """Main student recommendation page."""
    st.set_page_config(
        page_title="My Reading Recommendations",
        page_icon="📚",
        layout="wide"
    )

    # Header
    st.title("📖 Your Reading Recommendations")
    st.markdown("*Discover your next favorite book!*")

    # Load data
    books_df, students_df, checkouts_df, recommender, explainer = load_data()

    # Student selector (in real system, this would come from authentication)
    st.sidebar.header("Student Profile")

    # Select student
    student_options = students_df['student_id'].tolist()
    selected_student_id = st.sidebar.selectbox(
        "Select Student ID:",
        student_options,
        help="In the real system, this would be automatic based on login"
    )

    # Get student info
    student_info = students_df[students_df['student_id'] == selected_student_id].iloc[0]

    # Display student profile in sidebar
    st.sidebar.write(f"**Name:** {selected_student_id}")
    st.sidebar.write(f"**Grade:** {student_info['grade']}")
    st.sidebar.write(f"**School:** {student_info['school']}")
    st.sidebar.write(f"**Reading Profile:** {student_info['reading_profile']}")
    st.sidebar.write(f"**Books Read:** {student_info['total_checkouts']}")
    st.sidebar.write(f"**Favorite Genre:** {student_info['favorite_genre']}")

    # Main content
    col1, col2 = st.columns([2, 1])

    with col2:
        st.header("📊 Your Reading Stats")
        st.metric("Books This Year", student_info['total_checkouts'])
        st.metric("Genres Explored", student_info['unique_genres'])
        st.metric("Average Book Length", f"{student_info['avg_book_length']:.0f} pages")

    with col1:
        st.header("🎯 Recommended Just for You")

        # Get recommendations
        with st.spinner('Finding perfect books for you...'):
            try:
                recommendations = recommender.recommend_for_user(selected_student_id, n_recommendations=5)

                # Get reading history for explanations
                student_checkouts = checkouts_df[checkouts_df['student_id'] == selected_student_id]['book_id'].tolist()
                reading_history = []
                for book_id in student_checkouts[:3]:
                    book_info = books_df[books_df['book_id'] == book_id]
                    if len(book_info) > 0:
                        book = book_info.iloc[0]
                        reading_history.append({
                            'title': book['title'],
                            'author': book['author'],
                            'genre': book['genre']
                        })

                # Generate explanations
                enhanced_recommendations = explainer.generate_batch_explanations(
                    recommendations, student_info['grade'], reading_history
                )

                if enhanced_recommendations:
                    # Featured recommendation (first one)
                    st.subheader("⭐ Top Pick for You")
                    top_rec = enhanced_recommendations[0]

                    # Get full book info
                    book_data = books_df[books_df['book_id'] == top_rec['book_id']].iloc[0]

                    with st.container():
                        st.markdown(
                            f"""
                            <div style="
                                border: 2px solid #4CAF50;
                                border-radius: 10px;
                                padding: 20px;
                                background-color: #f9f9f9;
                                margin: 20px 0;
                            ">
                                <h3>📚 {top_rec['title']}</h3>
                                <p><strong>by {top_rec['author']}</strong></p>
                                <p><em>{book_data['genre']} • {book_data['pages']} pages • {book_data['reading_level']}L</em></p>
                                <p style="font-style: italic; color: #666;">{book_data['description']}</p>
                                <p style="background-color: #e8f5e8; padding: 10px; border-radius: 5px;">
                                    💡 <strong>Why this book?</strong> {top_rec['explanation']}
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    # Action buttons for top pick
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("📖 I'm Interested!", key="interested_top"):
                            st.success("Great choice! Ask your librarian to help you find this book.")

                    with col_btn2:
                        if st.button("📚 Find in Library", key="find_top"):
                            st.info("Check with your school librarian for availability.")

                    with col_btn3:
                        if st.button("💾 Save for Later", key="save_top"):
                            st.success("Saved to your reading list!")

                    # Other recommendations
                    if len(enhanced_recommendations) > 1:
                        st.subheader("📚 More Great Books for You")

                        for i, rec in enumerate(enhanced_recommendations[1:], 2):
                            book_data = books_df[books_df['book_id'] == rec['book_id']].iloc[0]

                            with st.expander(f"{i}. {rec['title']} by {rec['author']}", expanded=False):
                                col_book1, col_book2 = st.columns([2, 1])

                                with col_book1:
                                    st.write(f"**Genre:** {rec['genre']}")
                                    st.write(f"**Description:** {book_data['description']}")
                                    st.info(f"💡 {rec['explanation']}")

                                with col_book2:
                                    st.metric("Reading Level", f"{book_data['reading_level']}L")
                                    st.metric("Pages", book_data['pages'])

                                    copies = book_data['copies_available']
                                    if copies > 0:
                                        st.success(f"✅ {copies} available")
                                    else:
                                        st.error("❌ No copies")

                                # Quick action buttons
                                if st.button(f"I want to read this!", key=f"want_{i}"):
                                    st.success("Added to your interest list!")

                else:
                    st.warning("No recommendations available right now. Try checking back later!")

            except Exception as e:
                st.error(f"Sorry, we couldn't load recommendations right now. Error: {str(e)}")

    # Reading history section
    if student_info['total_checkouts'] > 0:
        st.header("📖 Books You've Read Recently")

        recent_checkouts = checkouts_df[checkouts_df['student_id'] == selected_student_id].tail(3)

        if len(recent_checkouts) > 0:
            cols = st.columns(len(recent_checkouts))

            for i, (_, checkout) in enumerate(recent_checkouts.iterrows()):
                book_data = books_df[books_df['book_id'] == checkout['book_id']].iloc[0]

                with cols[i]:
                    st.write(f"**{book_data['title']}**")
                    st.write(f"by {book_data['author']}")
                    st.write(f"*{book_data['genre']}*")
                    st.write(f"Checked out: {checkout['checkout_date']}")

    # Footer
    st.markdown("---")
    st.markdown("*Need help finding a book? Ask your school librarian!*")


def main():
    """Run the student page."""
    student_page()


if __name__ == "__main__":
    main()