from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reading_lift_poc.pipeline import apply_librarian_actions, build_demo_bundle


st.set_page_config(page_title="Fulton County Reading Lift", layout="wide")


@st.cache_data(show_spinner=False)
def load_bundle():
    return build_demo_bundle()


def ensure_state() -> None:
    if "librarian_actions" not in st.session_state:
        st.session_state.librarian_actions = []
    if "saved_books" not in st.session_state:
        st.session_state.saved_books = set()


def main() -> None:
    ensure_state()
    bundle = load_bundle()
    recommendations = apply_librarian_actions(bundle.recommendations, bundle.catalog, st.session_state.librarian_actions)
    _inject_styles()

    st.sidebar.title("Reading Lift POC")
    role = st.sidebar.radio("View", ["Student", "Librarian", "District leader"], index=0)
    st.sidebar.caption("Nightly batch proof of concept using synthetic Destiny-style data.")
    st.sidebar.write(f"Last batch refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if role == "Student":
        render_student_view(bundle.students, recommendations)
    elif role == "Librarian":
        render_librarian_view(bundle, recommendations)
    else:
        render_district_view(bundle, recommendations)


def render_student_view(students: pd.DataFrame, recommendations: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>Student recommendation page</div>", unsafe_allow_html=True)
    st.markdown("# Your next library picks")
    student_row = st.selectbox(
        "Student",
        options=students["student_id"],
        format_func=lambda student_id: _student_label(students, student_id),
        index=int(students.index[students["student_id"] == "STU-003"][0]),
    )
    student = students.loc[students["student_id"] == student_row].iloc[0]
    student_recs = recommendations.loc[recommendations["student_id"] == student_row].sort_values("rank")

    if student_recs.empty:
        st.info("We do not have personalized picks for you yet. Browse popular books for your grade and check back after the next nightly refresh.")
        return

    hero = student_recs.iloc[0]
    left, right = st.columns([1.1, 1.4])
    with left:
        st.markdown(
            f"""
            <div class='cover-card'>
                <div class='cover-label'>Top pick</div>
                <div class='cover-title'>{hero['title']}</div>
                <div class='cover-author'>{hero['author']}</div>
                <div class='cover-meta'>{hero['genre']} • {hero['availability']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(f"## {hero['title']}")
        st.write(hero["explanation"])
        badge_col1, badge_col2, badge_col3 = st.columns(3)
        badge_col1.metric("Why this showed up", hero["strategy"].replace("_", " ").title())
        badge_col2.metric("Display state", hero.get("display_state", hero["review_state"]).replace("_", " ").title())
        badge_col3.metric("Availability", hero["availability"])
        action_col1, action_col2 = st.columns(2)
        if action_col1.button("Save for later", key=f"save-{hero['book_id']}", width="stretch"):
            st.session_state.saved_books.add(hero["book_id"])
        if action_col2.button("I'm interested", key=f"interest-{hero['book_id']}", width="stretch"):
            st.session_state.saved_books.add(hero["book_id"])
        if st.session_state.saved_books:
            st.caption(f"Saved titles in this session: {len(st.session_state.saved_books)}")

    st.markdown("### More like this")
    for _, row in student_recs.iloc[1:].iterrows():
        st.markdown(
            f"""
            <div class='list-card'>
                <div>
                    <div class='list-title'>{row['title']}</div>
                    <div class='list-copy'>{row['explanation']}</div>
                </div>
                <div class='list-badge'>{row.get('display_state', row['review_state']).replace('_', ' ').title()}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_librarian_view(bundle, recommendations: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>Librarian review workspace</div>", unsafe_allow_html=True)
    st.markdown("# Review queue and student context")
    schools = bundle.students[["school_id", "school_name"]].drop_duplicates().sort_values("school_name")
    school_id = st.selectbox(
        "School",
        options=schools["school_id"],
        format_func=lambda value: schools.loc[schools["school_id"] == value, "school_name"].iloc[0],
    )
    school_students = bundle.students.loc[bundle.students["school_id"] == school_id].sort_values(["grade", "student_name"])

    left, center, right = st.columns([1.0, 1.2, 1.3])
    with left:
        selected_student_id = st.selectbox(
            "Student or homeroom",
            options=school_students["student_id"],
            format_func=lambda value: _student_label(bundle.students, value),
        )
        queue = recommendations.loc[
            (recommendations["school_id"] == school_id) & (recommendations["review_state"].isin(["needs_review", "approved", "pinned", "replaced"]))
        ][["student_name", "title", "review_state", "confidence_band"]].copy()
        queue.columns = ["Student", "Title", "State", "Confidence"]
        st.markdown("### Queue snapshot")
        st.dataframe(queue, hide_index=True, width="stretch")

    student_recs = recommendations.loc[recommendations["student_id"] == selected_student_id].sort_values("rank")
    target_student = bundle.students.loc[bundle.students["student_id"] == selected_student_id].iloc[0]
    choice_labels = [f"{row.rank}. {row.title}" for row in student_recs.itertuples()]
    selected_label = center.radio("Recommendation detail", choice_labels, index=0 if choice_labels else None)
    selected_rank = int(selected_label.split(".", 1)[0]) if choice_labels else 1
    selected_rec = student_recs.loc[student_recs["rank"] == selected_rank].iloc[0] if not student_recs.empty else None

    with center:
        if selected_rec is not None:
            st.markdown("### Recommendation detail")
            st.write(selected_rec["explanation"])
            st.caption(
                f"Provenance: {selected_rec['strategy'].replace('_', ' ')} | Confidence: {selected_rec['confidence_band']} | Availability: {selected_rec['availability']}"
            )
            st.metric("Current state", selected_rec.get("display_state", selected_rec["review_state"]).replace("_", " ").title())
            blocked = bundle.blocked_recommendations.loc[bundle.blocked_recommendations["student_id"] == selected_student_id][["title", "blocked_reason", "final_score"]]
            if not blocked.empty:
                with st.expander("Guardrail log"):
                    st.dataframe(blocked, hide_index=True, width="stretch")

    with right:
        if selected_rec is not None:
            st.markdown("### Actions")
            if st.button("Approve", width="stretch"):
                _record_action("approve", selected_rec.to_dict(), target_student.to_dict())
                st.rerun()
            if st.button("Pin to top", width="stretch"):
                _record_action("pin", selected_rec.to_dict(), target_student.to_dict())
                st.rerun()
            if st.button("Suppress", width="stretch"):
                _record_action("suppress", selected_rec.to_dict(), target_student.to_dict())
                st.rerun()
            replacement_options = bundle.catalog.loc[
                (bundle.catalog["grade_min"] <= target_student["grade"]) & (bundle.catalog["grade_max"] >= target_student["grade"]),
                ["book_id", "title"],
            ]
            replacement_book_id = st.selectbox(
                "Replace with",
                options=replacement_options["book_id"],
                format_func=lambda value: replacement_options.loc[replacement_options["book_id"] == value, "title"].iloc[0],
            )
            if st.button("Apply replacement", width="stretch"):
                _record_action("replace", selected_rec.to_dict(), target_student.to_dict(), replacement_book_id=replacement_book_id)
                st.rerun()

        if st.session_state.librarian_actions:
            st.markdown("### Audit trail")
            audit = pd.DataFrame(st.session_state.librarian_actions).sort_values("timestamp", ascending=False)
            st.dataframe(audit[["timestamp", "student_name", "action_type", "title"]], hide_index=True, width="stretch")


def render_district_view(bundle, recommendations: pd.DataFrame) -> None:
    school_metrics = _recalculate_school_metrics(bundle, recommendations)
    st.markdown("<div class='eyebrow'>District pilot dashboard</div>", unsafe_allow_html=True)
    st.markdown("# Pilot health and checkout lift")
    top = st.columns(4)
    top[0].metric("Students exposed", f"{int(recommendations['student_id'].nunique())}/{len(bundle.students)}")
    top[1].metric("Exposure rate", f"{recommendations['student_id'].nunique() / len(bundle.students):.0%}")
    top[2].metric("Approval rate", f"{school_metrics['approval_rate'].mean():.0%}")
    top[3].metric("Average checkout lift", f"{school_metrics['checkout_lift_pct'].mean():.1f}%")

    chart = bundle.weekly_metrics.copy()
    adjusted = school_metrics[["school_id", "approval_rate", "exposure_rate", "checkout_lift_pct"]]
    chart = chart.drop(columns=["approval_rate", "exposure_rate", "checkout_lift_pct"]).merge(adjusted, on="school_id", how="left")
    chart["checkout_lift_pct"] = chart["checkout_lift_pct"] - 3 + (chart["week"] * 0.7)
    figure = px.line(chart, x="week", y="checkout_lift_pct", color="school_name", markers=True)
    figure.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20), legend_title_text="School")
    st.plotly_chart(figure, width="stretch")

    left, right = st.columns([1.1, 0.9])
    with left:
        display = school_metrics[["school_name", "recommendation_volume", "exposure_rate", "approval_rate", "override_rate", "checkout_lift_pct"]].copy()
        display.columns = ["School", "Recommendation volume", "Exposure", "Approval", "Override", "Checkout lift %"]
        st.markdown("### School comparison")
        st.dataframe(display, hide_index=True, width="stretch")

    with right:
        st.markdown("### Recommendation quality signals")
        st.metric("Needs review", int((recommendations["review_state"] == "needs_review").sum()))
        st.metric("Pinned by librarians", int((recommendations["review_state"] == "pinned").sum()))
        st.metric("Staff replacements", int((recommendations["review_state"] == "replaced").sum()))
        st.metric("Auto-published", int((recommendations["review_state"] == "auto_published").sum()))

    with st.expander("Nightly batch debug log"):
        st.dataframe(bundle.debug_log, hide_index=True, width="stretch")


def _recalculate_school_metrics(bundle, recommendations: pd.DataFrame) -> pd.DataFrame:
    recommendation_counts = recommendations.groupby("school_id").size().rename("recommendation_volume")
    exposures = recommendations.groupby("school_id")["student_id"].nunique().rename("students_exposed")
    student_counts = bundle.students.groupby("school_id").size().rename("student_count")
    approvals = recommendations.loc[recommendations["review_state"].isin(["approved", "auto_published", "pinned", "replaced"])].groupby("school_id").size().rename("approved_count")
    overrides = recommendations.loc[recommendations["review_state"].isin(["pinned", "replaced"])].groupby("school_id").size().rename("override_count")
    school_metrics = pd.concat([student_counts, recommendation_counts, exposures, approvals, overrides], axis=1).fillna(0).reset_index()
    school_metrics = school_metrics.merge(bundle.schools, on="school_id", how="left")
    school_metrics["exposure_rate"] = school_metrics["students_exposed"] / school_metrics["student_count"].replace(0, 1)
    school_metrics["approval_rate"] = school_metrics["approved_count"] / school_metrics["recommendation_volume"].replace(0, 1)
    school_metrics["override_rate"] = school_metrics["override_count"] / school_metrics["recommendation_volume"].replace(0, 1)
    school_metrics["checkout_lift_pct"] = (6 + (school_metrics["exposure_rate"] * 8) + (school_metrics["approval_rate"] * 5)).round(1)
    return school_metrics.sort_values("checkout_lift_pct", ascending=False)


def _record_action(action_type: str, rec: dict, student: dict, replacement_book_id: str | None = None) -> None:
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action_type": action_type,
        "student_id": student["student_id"],
        "student_name": student["student_name"],
        "school_id": student["school_id"],
        "school_name": student["school_name"],
        "grade": student["grade"],
        "homeroom": student["homeroom"],
        "book_id": rec["book_id"],
        "title": rec["title"],
        "anchor_title": rec.get("anchor_title", "librarian curation"),
    }
    if replacement_book_id:
        payload["replacement_book_id"] = replacement_book_id
    st.session_state.librarian_actions.append(payload)


def _student_label(students: pd.DataFrame, student_id: str) -> str:
    row = students.loc[students["student_id"] == student_id].iloc[0]
    return f"{row['student_name']} • Grade {row['grade']} • {row['school_name']}"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f6f1e8;
            color: #172321;
        }
        [data-testid='stSidebar'] {
            background: #e9dfcf;
        }
        h1, h2, h3 {
            color: #172321;
        }
        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.78rem;
            color: #83684d;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }
        .cover-card {
            background: linear-gradient(160deg, #344c43 0%, #1f302a 100%);
            border-radius: 22px;
            padding: 28px;
            min-height: 330px;
            color: #f9f6f0;
            box-shadow: 0 18px 36px rgba(23, 35, 33, 0.18);
        }
        .cover-label {
            font-size: 0.8rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            opacity: 0.8;
            margin-bottom: 20px;
        }
        .cover-title {
            font-family: Georgia, serif;
            font-size: 2rem;
            line-height: 1.05;
            margin-bottom: 10px;
        }
        .cover-author {
            font-size: 1rem;
            margin-bottom: 10px;
        }
        .cover-meta {
            font-size: 0.95rem;
            opacity: 0.9;
        }
        .list-card {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 16px;
            background: #fffdf8;
            border: 1px solid #dccfb8;
            border-radius: 16px;
            padding: 16px 18px;
            margin-bottom: 12px;
        }
        .list-title {
            font-weight: 700;
            margin-bottom: 4px;
        }
        .list-copy {
            color: #37443f;
        }
        .list-badge {
            white-space: nowrap;
            background: #dfe8e2;
            color: #1f302a;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.82rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()