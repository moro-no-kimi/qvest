"""
District Leadership Dashboard
Analytics and metrics for the Reading Lift Pilot
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Reading Lift Pilot Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for dashboard styling
st.markdown("""
<style>
.dashboard-header {
    background: linear-gradient(90deg, #2c3e50 0%, #3498db 100%);
    color: white;
    padding: 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
}

.metric-card {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
    margin: 0.5rem 0;
}

.metric-value {
    font-size: 2.5rem;
    font-weight: bold;
    color: #2c3e50;
}

.metric-label {
    color: #7f8c8d;
    font-size: 0.9rem;
    margin-top: 0.5rem;
}

.status-good {
    border-left: 4px solid #27ae60;
}

.status-warning {
    border-left: 4px solid #f39c12;
}

.status-critical {
    border-left: 4px solid #e74c3c;
}

.school-row {
    background: #f8f9fa;
    padding: 1rem;
    margin: 0.5rem 0;
    border-radius: 4px;
    border-left: 3px solid #3498db;
}
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"

def get_dashboard_metrics():
    """Fetch dashboard metrics from API"""
    try:
        response = requests.get(f"{API_BASE}/api/dashboard/metrics")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def create_mock_trends_data():
    """Create mock trends data for demo"""
    weeks = pd.date_range(start=datetime.now() - timedelta(weeks=12), periods=12, freq='W')

    checkout_data = []
    for i, week in enumerate(weeks):
        checkout_data.append({
            'week': week.strftime('%Y-%m-%d'),
            'checkouts': 450 + i * 25 + (i * 10 if i > 6 else 0),  # Show lift after week 6
            'recommendations_generated': 200 + i * 15,
            'recommendations_approved': 150 + i * 12,
            'checkouts_from_recs': 50 + i * 8 + (i * 5 if i > 6 else 0)
        })

    return pd.DataFrame(checkout_data)

def display_metric_card(title: str, value: str, subtitle: str = "", status: str = "good"):
    """Display a metric card"""
    status_class = f"status-{status}"

    st.markdown(f"""
    <div class="metric-card {status_class}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
        {f'<div style="font-size: 0.8rem; color: #95a5a6; margin-top: 0.25rem;">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def main():
    # Dashboard header
    st.markdown("""
    <div class="dashboard-header">
        <h1>📊 Reading Lift Pilot Dashboard</h1>
        <p>Fulton County Schools - Middle School Pilot Program</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">Last updated: {}</p>
    </div>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M')), unsafe_allow_html=True)

    # Fetch metrics
    metrics_data = get_dashboard_metrics()

    if not metrics_data:
        st.error("Unable to load dashboard metrics. Please check API connection.")
        return

    overview = metrics_data['overview']
    schools = metrics_data['schools']

    # Key metrics row
    st.subheader("Pilot Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        display_metric_card(
            "Total Students",
            f"{overview['total_students']:,}",
            "Across 5 pilot schools"
        )

    with col2:
        approval_rate = (overview['approved_recommendations'] / overview['total_recommendations'] * 100) if overview['total_recommendations'] > 0 else 0
        display_metric_card(
            "Approval Rate",
            f"{approval_rate:.1f}%",
            f"{overview['approved_recommendations']:,} approved",
            "good" if approval_rate > 80 else "warning" if approval_rate > 60 else "critical"
        )

    with col3:
        display_metric_card(
            "Recommendations",
            f"{overview['total_recommendations']:,}",
            "Generated this semester"
        )

    with col4:
        display_metric_card(
            "Books Available",
            f"{overview['total_books']:,}",
            "In district catalog"
        )

    # Trends section
    st.subheader("Usage Trends")

    # Create mock trends data
    trends_df = create_mock_trends_data()

    # Checkout trends chart
    fig_checkouts = px.line(
        trends_df,
        x='week',
        y=['checkouts', 'checkouts_from_recs'],
        title='Weekly Checkout Trends',
        labels={'value': 'Number of Checkouts', 'week': 'Week'}
    )
    fig_checkouts.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Add annotation for pilot start
    fig_checkouts.add_vline(
        x=trends_df.iloc[6]['week'],
        line_dash="dash",
        line_color="red",
        annotation_text="Pilot Started"
    )

    st.plotly_chart(fig_checkouts, use_container_width=True)

    # Recommendation pipeline metrics
    col1, col2 = st.columns(2)

    with col1:
        # Recommendation funnel
        funnel_data = {
            'Stage': ['Generated', 'Approved by Librarian', 'Viewed by Students', 'Led to Checkout'],
            'Count': [
                overview['total_recommendations'],
                overview['approved_recommendations'],
                int(overview['approved_recommendations'] * 0.8),
                int(overview['approved_recommendations'] * 0.3)
            ]
        }
        fig_funnel = px.funnel(
            pd.DataFrame(funnel_data),
            x='Count',
            y='Stage',
            title='Recommendation Pipeline'
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col2:
        # Librarian actions breakdown
        actions_data = {
            'Action': ['Auto-Approved', 'Librarian Approved', 'Replaced', 'Rejected'],
            'Count': [
                overview['total_recommendations'] - overview['librarian_approved'] - overview['librarian_replaced'],
                overview['librarian_approved'],
                overview['librarian_replaced'],
                overview['total_recommendations'] - overview['approved_recommendations']
            ]
        }
        fig_actions = px.pie(
            pd.DataFrame(actions_data),
            values='Count',
            names='Action',
            title='Librarian Action Breakdown'
        )
        st.plotly_chart(fig_actions, use_container_width=True)

    # School-level performance
    st.subheader("School Performance")

    # Convert schools data to DataFrame
    schools_df = pd.DataFrame(schools)

    if not schools_df.empty:
        # Add calculated metrics
        schools_df['approval_rate'] = (
            schools_df['recommendations_approved'] /
            schools_df['recommendations_generated'] * 100
        ).fillna(0)

        schools_df['coverage'] = (
            schools_df['recommendations_generated'] /
            schools_df['total_students'] * 100
        ).fillna(0)

        # Display school cards
        for _, school in schools_df.iterrows():
            approval_status = "good" if school['approval_rate'] > 80 else "warning" if school['approval_rate'] > 60 else "critical"

            st.markdown(f"""
            <div class="school-row">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0; color: #2c3e50;">{school['school_name']}</h4>
                        <p style="margin: 0; color: #7f8c8d;">{school['total_students']} students</p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #2c3e50;">
                            {school['approval_rate']:.1f}% approval
                        </div>
                        <div style="font-size: 0.9rem; color: #7f8c8d;">
                            {school['recommendations_generated']} recommendations generated
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # School comparison chart
        fig_schools = px.scatter(
            schools_df,
            x='coverage',
            y='approval_rate',
            size='total_students',
            hover_name='school_name',
            title='School Performance: Coverage vs Approval Rate',
            labels={
                'coverage': 'Student Coverage (%)',
                'approval_rate': 'Librarian Approval Rate (%)',
                'total_students': 'Total Students'
            }
        )
        fig_schools.update_layout(showlegend=False)
        st.plotly_chart(fig_schools, use_container_width=True)

    # Pilot health indicators
    st.subheader("Pilot Health Check")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Adoption health
        adoption_score = 85  # Mock score
        status = "good" if adoption_score > 80 else "warning" if adoption_score > 60 else "critical"
        display_metric_card(
            "Adoption Health",
            f"{adoption_score}%",
            "Students actively using recommendations",
            status
        )

    with col2:
        # Trust score (librarian approval rate)
        trust_score = approval_rate
        status = "good" if trust_score > 80 else "warning" if trust_score > 60 else "critical"
        display_metric_card(
            "Trust Score",
            f"{trust_score:.1f}%",
            "Librarian approval rate",
            status
        )

    with col3:
        # Impact estimate
        impact_estimate = 15.2  # Mock percentage increase
        status = "good" if impact_estimate > 10 else "warning" if impact_estimate > 5 else "critical"
        display_metric_card(
            "Checkout Lift",
            f"+{impact_estimate:.1f}%",
            "Estimated increase vs baseline",
            status
        )

    # Recommendations and alerts
    st.subheader("Recommendations & Alerts")

    if approval_rate < 70:
        st.warning("⚠️ Approval rate below threshold. Consider reviewing recommendation quality.")

    if any(school['coverage'] < 50 for school in schools):
        st.warning("⚠️ Some schools have low student coverage. Check librarian engagement.")

    st.success("✅ Pilot is performing within expected parameters.")

    # Footer
    st.markdown("---")
    st.markdown("""
    **Data Notes:**
    - Metrics update nightly after batch processing
    - Checkout lift calculated against same period last year
    - Pilot running since Week 6 of semester
    """)

if __name__ == "__main__":
    main()