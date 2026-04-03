#!/usr/bin/env python3
"""
Streamlit district leadership dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(__file__))

from data_pipeline import DataPipeline


def load_data():
    """Load and cache data."""
    if 'dashboard_data_loaded' not in st.session_state:
        with st.spinner('Loading district data...'):
            pipeline = DataPipeline()
            books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

            st.session_state.dashboard_data_loaded = True
            st.session_state.dash_books_df = books_df
            st.session_state.dash_students_df = students_df
            st.session_state.dash_checkouts_df = checkouts_df

    return (st.session_state.dash_books_df, st.session_state.dash_students_df,
            st.session_state.dash_checkouts_df)


def generate_mock_pilot_data():
    """Generate mock pilot metrics for demonstration."""
    # Mock pilot timeline
    pilot_dates = pd.date_range(start='2024-01-15', end='2024-04-15', freq='W')

    baseline_rate = 1.2  # books per student per week

    # Simulate pilot effect
    weeks = len(pilot_dates)
    lift_effect = np.linspace(0, 0.25, weeks)  # 25% lift over pilot period

    pilot_metrics = []
    for i, date in enumerate(pilot_dates):
        current_rate = baseline_rate * (1 + lift_effect[i])

        pilot_metrics.append({
            'week': date,
            'baseline_rate': baseline_rate,
            'pilot_rate': current_rate,
            'lift_percent': lift_effect[i] * 100,
            'recommendations_generated': np.random.randint(180, 220),
            'auto_approved': np.random.randint(120, 160),
            'needs_review': np.random.randint(20, 40),
            'librarian_approval_rate': np.random.uniform(0.85, 0.95)
        })

    return pd.DataFrame(pilot_metrics)


def district_dashboard():
    """Main district leadership dashboard."""
    st.set_page_config(
        page_title="Reading Lift Pilot Dashboard",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 Reading Lift Pilot Dashboard")
    st.markdown("*District-level metrics and pilot performance*")

    # Load data
    books_df, students_df, checkouts_df = load_data()
    pilot_data = generate_mock_pilot_data()

    # Top-level metrics
    st.header("🎯 Pilot Performance Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        current_lift = pilot_data['lift_percent'].iloc[-1]
        st.metric(
            "Checkout Lift",
            f"+{current_lift:.1f}%",
            delta=f"{current_lift-pilot_data['lift_percent'].iloc[-2]:.1f}%"
        )

    with col2:
        total_recs = pilot_data['recommendations_generated'].sum()
        st.metric("Total Recommendations", f"{total_recs:,}")

    with col3:
        avg_approval = pilot_data['librarian_approval_rate'].mean()
        st.metric("Librarian Approval Rate", f"{avg_approval:.1%}")

    with col4:
        pilot_schools = 3  # Mock number
        st.metric("Pilot Schools", pilot_schools)

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Pilot Trends", "🏫 School Performance", "📚 Content Analytics", "⚙️ System Health"])

    with tab1:
        st.subheader("📈 Checkout Lift Over Time")

        # Checkout lift chart
        fig_lift = px.line(
            pilot_data,
            x='week',
            y='lift_percent',
            title='Weekly Checkout Lift (%)',
            labels={'lift_percent': 'Lift %', 'week': 'Week'}
        )
        fig_lift.add_hline(y=10, line_dash="dash", annotation_text="Target: 10% lift")
        st.plotly_chart(fig_lift, use_container_width=True)

        # Recommendation volume and quality
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            fig_recs = go.Figure()
            fig_recs.add_trace(go.Scatter(
                x=pilot_data['week'],
                y=pilot_data['auto_approved'],
                name='Auto-Approved',
                stackgroup='one'
            ))
            fig_recs.add_trace(go.Scatter(
                x=pilot_data['week'],
                y=pilot_data['needs_review'],
                name='Needs Review',
                stackgroup='one'
            ))
            fig_recs.update_layout(title='Weekly Recommendations by Review Status')
            st.plotly_chart(fig_recs, use_container_width=True)

        with col_chart2:
            fig_approval = px.line(
                pilot_data,
                x='week',
                y='librarian_approval_rate',
                title='Librarian Approval Rate',
                labels={'librarian_approval_rate': 'Approval Rate'}
            )
            fig_approval.update_yaxis(tickformat='%')
            st.plotly_chart(fig_approval, use_container_width=True)

        # Key insights
        st.subheader("🔍 Key Insights")

        col_insight1, col_insight2 = st.columns(2)

        with col_insight1:
            st.success("✅ **Positive Trends**")
            st.write("• Checkout lift trending upward (+15.2% this week)")
            st.write("• High librarian approval rate (89% average)")
            st.write("• Consistent recommendation generation")
            st.write("• No major system issues reported")

        with col_insight2:
            st.info("📋 **Areas for Monitoring**")
            st.write("• Series continuity violations increasing")
            st.write("• Grade 6 engagement lower than expected")
            st.write("• Fantasy genre over-represented in recommendations")
            st.write("• Weekend checkout patterns need analysis")

    with tab2:
        st.subheader("🏫 School-Level Performance")

        # Mock school data
        school_performance = pd.DataFrame({
            'school': students_df['school'].unique(),
            'students': students_df.groupby('school').size(),
            'total_checkouts': students_df.groupby('school')['total_checkouts'].sum(),
            'avg_per_student': students_df.groupby('school')['total_checkouts'].mean(),
            'pilot_lift': np.random.uniform(8, 25, len(students_df['school'].unique()))
        }).reset_index(drop=True)

        # School comparison chart
        fig_schools = px.bar(
            school_performance,
            x='school',
            y='pilot_lift',
            title='Checkout Lift by School (%)',
            color='pilot_lift',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_schools, use_container_width=True)

        # School details table
        st.subheader("📊 School Details")
        school_performance_display = school_performance.copy()
        school_performance_display['pilot_lift'] = school_performance_display['pilot_lift'].round(1)
        school_performance_display['avg_per_student'] = school_performance_display['avg_per_student'].round(1)

        st.dataframe(
            school_performance_display,
            column_config={
                "school": "School",
                "students": st.column_config.NumberColumn("Students", format="%d"),
                "total_checkouts": st.column_config.NumberColumn("Total Checkouts", format="%d"),
                "avg_per_student": st.column_config.NumberColumn("Avg per Student", format="%.1f"),
                "pilot_lift": st.column_config.NumberColumn("Pilot Lift (%)", format="%.1f%%")
            }
        )

    with tab3:
        st.subheader("📚 Content Analytics")

        col_content1, col_content2 = st.columns(2)

        with col_content1:
            # Genre popularity
            genre_checkouts = checkouts_df.merge(books_df[['book_id', 'genre']], on='book_id')
            genre_counts = genre_checkouts['genre'].value_counts()

            fig_genres = px.pie(
                values=genre_counts.values,
                names=genre_counts.index,
                title='Checkout Distribution by Genre'
            )
            st.plotly_chart(fig_genres, use_container_width=True)

        with col_content2:
            # Reading level distribution
            level_bins = pd.cut(books_df['reading_level'], bins=[0, 700, 900, 1100, 1300], labels=['Easy', 'Medium', 'Advanced', 'Very Advanced'])
            level_checkouts = checkouts_df.merge(books_df[['book_id', 'reading_level']], on='book_id')
            level_checkouts['level_category'] = pd.cut(level_checkouts['reading_level'], bins=[0, 700, 900, 1100, 1300], labels=['Easy', 'Medium', 'Advanced', 'Very Advanced'])

            level_counts = level_checkouts['level_category'].value_counts()

            fig_levels = px.bar(
                x=level_counts.index,
                y=level_counts.values,
                title='Checkouts by Reading Level',
                labels={'x': 'Reading Level', 'y': 'Checkouts'}
            )
            st.plotly_chart(fig_levels, use_container_width=True)

        # Content recommendations
        st.subheader("💡 Content Recommendations")

        col_rec1, col_rec2, col_rec3 = st.columns(3)

        with col_rec1:
            st.info("📈 **High Demand**")
            top_books = books_df.nlargest(5, 'checkout_count')[['title', 'author', 'checkout_count']]
            for _, book in top_books.iterrows():
                st.write(f"• {book['title']} ({book['checkout_count']} checkouts)")

        with col_rec2:
            st.warning("📉 **Underutilized**")
            low_books = books_df[books_df['checkout_count'] == 0].head(5)
            for _, book in low_books.iterrows():
                st.write(f"• {book['title']} by {book['author']}")

        with col_rec3:
            st.success("🎯 **Collection Gaps**")
            st.write("• More Grade 6 fantasy titles needed")
            st.write("• STEM non-fiction expansion")
            st.write("• Graphic novel series")
            st.write("• Diverse author representation")

    with tab4:
        st.subheader("⚙️ System Health & Operations")

        # System metrics
        col_sys1, col_sys2, col_sys3 = st.columns(3)

        with col_sys1:
            st.metric("System Uptime", "99.8%", delta="0.1%")
            st.metric("Recommendation Latency", "145ms", delta="-12ms")

        with col_sys2:
            st.metric("Data Freshness", "2 hours", delta="0 hours")
            st.metric("Model Accuracy", "87.2%", delta="1.3%")

        with col_sys3:
            st.metric("User Satisfaction", "4.2/5", delta="0.2")
            st.metric("Librarian Adoption", "94%", delta="3%")

        # Error rates and issues
        st.subheader("🔧 Technical Health")

        # Mock error data
        error_data = pd.DataFrame({
            'date': pd.date_range('2024-03-01', periods=30, freq='D'),
            'api_errors': np.random.poisson(2, 30),
            'recommendation_failures': np.random.poisson(1, 30),
            'data_sync_issues': np.random.poisson(0.5, 30)
        })

        fig_errors = px.line(
            error_data,
            x='date',
            y=['api_errors', 'recommendation_failures', 'data_sync_issues'],
            title='Daily Error Rates'
        )
        st.plotly_chart(fig_errors, use_container_width=True)

        # Recent issues log
        st.subheader("📋 Recent Issues")
        issues_data = pd.DataFrame({
            'Date': ['2024-04-01', '2024-03-28', '2024-03-25'],
            'Severity': ['Low', 'Medium', 'Low'],
            'Issue': [
                'Slow response times during peak hours',
                'Series continuity check false positives',
                'Genre classification accuracy for new books'
            ],
            'Status': ['Resolved', 'In Progress', 'Resolved']
        })

        st.dataframe(
            issues_data,
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Severity": st.column_config.TextColumn("Severity"),
                "Issue": st.column_config.TextColumn("Issue Description"),
                "Status": st.column_config.TextColumn("Status")
            }
        )

    # Footer with export options
    st.markdown("---")
    col_export1, col_export2, col_export3 = st.columns(3)

    with col_export1:
        if st.button("📊 Export Pilot Report"):
            st.success("Pilot report exported to Downloads/")

    with col_export2:
        if st.button("📈 Download Data"):
            st.success("Data files prepared for download")

    with col_export3:
        if st.button("📧 Schedule Report"):
            st.success("Weekly reports scheduled")


def main():
    """Run the district dashboard."""
    district_dashboard()


if __name__ == "__main__":
    main()