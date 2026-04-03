#!/usr/bin/env python3
"""
Main demo application for Fulton County Reading Lift Pilot.
"""

import streamlit as st
import subprocess
import os
import sys
from pathlib import Path


def main_demo():
    """Main demo selection page."""
    st.set_page_config(
        page_title="Reading Lift Pilot Demo",
        page_icon="📚",
        layout="wide"
    )

    # Header
    st.title("📚 Fulton County Reading Lift Pilot")
    st.markdown("### AI-Powered Book Recommendation System Demo")

    st.markdown("---")

    # Demo description
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        **Welcome to the Reading Lift Pilot demonstration!**

        This system combines collaborative filtering, content-based recommendations,
        and policy guardrails to help middle school students discover books they'll love.

        **Key Features:**
        - 🤝 **Collaborative Filtering**: Recommendations based on similar students' reading patterns
        - 📖 **Content Analysis**: Matches books by genre, theme, reading level, and series
        - 🔒 **Policy Guardrails**: Ensures age-appropriate and available recommendations
        - 🤖 **LLM Explanations**: Natural language explanations for each suggestion
        - 👩‍🏫 **Librarian Oversight**: Review and approval workflow for staff
        - 📊 **District Analytics**: Pilot metrics and performance tracking
        """)

    with col2:
        st.info("""
        **Demo Components:**

        📱 **Student Page**
        Book recommendations with explanations

        👩‍🏫 **Librarian Workspace**
        Review and approval interface

        📊 **District Dashboard**
        Pilot metrics and analytics

        🔧 **API Backend**
        RESTful recommendation service
        """)

    # Demo interface selection
    st.markdown("---")
    st.header("🚀 Choose Demo Interface")

    col_demo1, col_demo2, col_demo3 = st.columns(3)

    with col_demo1:
        st.subheader("📱 Student Experience")
        st.markdown("See personalized book recommendations from a student's perspective.")

        if st.button("🎯 Open Student Page", key="student_demo", use_container_width=True):
            st.markdown("""
            **To run the Student Page:**
            ```bash
            streamlit run src/streamlit_student.py
            ```

            This will open in a new browser window at http://localhost:8501
            """)
            st.success("✅ Instructions displayed above!")

    with col_demo2:
        st.subheader("👩‍🏫 Librarian Workspace")
        st.markdown("Review AI recommendations and manage student reading suggestions.")

        if st.button("📋 Open Librarian Interface", key="librarian_demo", use_container_width=True):
            st.markdown("""
            **To run the Librarian Workspace:**
            ```bash
            streamlit run src/streamlit_librarian.py --server.port 8502
            ```

            This will open at http://localhost:8502
            """)
            st.success("✅ Instructions displayed above!")

    with col_demo3:
        st.subheader("📊 District Dashboard")
        st.markdown("Track pilot performance and system analytics.")

        if st.button("📈 Open District Dashboard", key="dashboard_demo", use_container_width=True):
            st.markdown("""
            **To run the District Dashboard:**
            ```bash
            streamlit run src/streamlit_dashboard.py --server.port 8503
            ```

            This will open at http://localhost:8503
            """)
            st.success("✅ Instructions displayed above!")

    # Technical demo section
    st.markdown("---")
    st.header("🔧 Technical Components")

    col_tech1, col_tech2 = st.columns(2)

    with col_tech1:
        st.subheader("🌐 API Backend")
        st.markdown("RESTful API for recommendation services.")

        if st.button("🚀 Start API Server", key="api_demo"):
            st.markdown("""
            **To run the API server:**
            ```bash
            python src/api.py
            ```

            API will be available at http://localhost:8000
            - Swagger docs: http://localhost:8000/docs
            - Health check: http://localhost:8000/health
            """)
            st.success("✅ API instructions displayed!")

    with col_tech2:
        st.subheader("🧪 Component Tests")
        st.markdown("Test individual recommendation components.")

        test_options = st.selectbox(
            "Select Component to Test:",
            [
                "Data Pipeline",
                "Collaborative Filtering",
                "Content-Based Recommendations",
                "Policy Guardrails",
                "Hybrid Recommender",
                "LLM Explanations"
            ]
        )

        if st.button("🧪 Run Component Test", key="test_demo"):
            test_commands = {
                "Data Pipeline": "python src/data_pipeline.py",
                "Collaborative Filtering": "python src/collaborative_filtering.py",
                "Content-Based Recommendations": "python src/content_based.py",
                "Policy Guardrails": "python src/policy_guardrails.py",
                "Hybrid Recommender": "python src/hybrid_recommender.py",
                "LLM Explanations": "python src/explanation_generator.py"
            }

            command = test_commands.get(test_options)
            if command:
                st.markdown(f"""
                **To test {test_options}:**
                ```bash
                {command}
                ```
                """)
                st.success(f"✅ {test_options} test command displayed!")

    # System requirements and setup
    st.markdown("---")
    st.header("⚙️ System Setup")

    col_setup1, col_setup2 = st.columns(2)

    with col_setup1:
        st.subheader("📦 Installation")
        st.markdown("""
        **First-time setup:**
        ```bash
        # Install dependencies
        pip install -r requirements.txt

        # Generate synthetic data
        python src/generate_data.py

        # Test data pipeline
        python src/data_pipeline.py
        ```
        """)

    with col_setup2:
        st.subheader("🗃️ Data Status")

        # Check if data files exist
        data_files = {
            "Books Catalog": "data/books_catalog.csv",
            "Students": "data/students.csv",
            "Checkout History": "data/checkout_history.csv"
        }

        for name, path in data_files.items():
            if os.path.exists(path):
                st.success(f"✅ {name}: Ready")
            else:
                st.error(f"❌ {name}: Missing")
                st.write(f"   Expected at: `{path}`")

    # Architecture overview
    st.markdown("---")
    st.header("🏗️ System Architecture")

    st.markdown("""
    ```mermaid
    graph TB
        A[Destiny Library Data] --> B[Data Pipeline]
        B --> C[Collaborative Filtering]
        B --> D[Content-Based Engine]
        B --> E[Policy Guardrails]

        C --> F[Hybrid Recommender]
        D --> F
        E --> F

        F --> G[LLM Explanations]
        G --> H[Student Interface]
        G --> I[Librarian Workspace]
        G --> J[District Dashboard]

        F --> K[API Backend]
        K --> L[External Integrations]
    ```

    **Data Flow:**
    1. **Ingestion**: Destiny catalog and checkout data
    2. **Processing**: Normalization, feature extraction, interaction matrices
    3. **Recommendation**: Hybrid scoring with collaborative + content + popularity signals
    4. **Guardrails**: Grade-level, content, and policy filtering
    5. **Explanation**: LLM-generated natural language explanations
    6. **Interfaces**: Student, librarian, and district-facing applications
    """)

    # Performance metrics
    st.markdown("---")
    st.header("📊 Expected Performance")

    col_perf1, col_perf2, col_perf3 = st.columns(3)

    with col_perf1:
        st.metric("Target Checkout Lift", "+10%", help="Minimum pilot success threshold")
        st.metric("Recommendation Latency", "<200ms", help="API response time")

    with col_perf2:
        st.metric("Librarian Approval Rate", ">80%", help="Staff trust and adoption")
        st.metric("System Availability", "99.5%", help="Uptime target")

    with col_perf3:
        st.metric("Data Freshness", "<4 hours", help="Nightly batch updates")
        st.metric("Coverage", ">90%", help="Students receiving recommendations")

    # Footer
    st.markdown("---")
    st.markdown("""
    **💡 Proof of Concept Notes:**
    - Uses synthetic data for demonstration
    - LLM explanations use mock templates (can connect to real APIs)
    - All interfaces are functional and demonstrate the complete workflow
    - Ready for pilot deployment with real Destiny data integration

    **🔗 Next Steps:**
    - Connect to real Destiny exports
    - Integrate with district authentication (ClassLink + Entra ID)
    - Deploy to district infrastructure
    - Configure librarian review workflows
    - Set up monitoring and analytics
    """)


if __name__ == "__main__":
    main_demo()