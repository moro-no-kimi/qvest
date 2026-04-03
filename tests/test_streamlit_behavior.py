from __future__ import annotations

from streamlit.testing.v1 import AppTest


APP_PATH = "reading_lift_poc/app.py"


def test_student_view_renders_hero_and_actions() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run()

    markdown_values = [item.value for item in app.markdown]
    button_labels = [button.label for button in app.button]

    assert "# Your next library picks" in markdown_values
    assert "## Scythe" in markdown_values
    assert "### More like this" in markdown_values
    assert "Save for later" in button_labels
    assert "I'm interested" in button_labels


def test_librarian_approve_updates_state_and_audit() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run()

    app.sidebar.radio[0].set_value("Librarian").run()
    app.button[0].click().run()

    assert len(app.session_state["librarian_actions"]) == 1
    assert app.session_state["librarian_actions"][0]["action_type"] == "approve"
    assert (app.metric[0].label, app.metric[0].value) == ("Current state", "Approved")


def test_pin_changes_student_top_pick() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run()

    app.sidebar.radio[0].set_value("Librarian").run()
    app.selectbox[1].set_value("STU-003").run()
    app.radio[0].set_value("2. Refugee").run()
    app.button[1].click().run()

    app.sidebar.radio[0].set_value("Student").run()
    app.selectbox[0].set_value("STU-003").run()

    markdown_values = [item.value for item in app.markdown]
    assert "## Refugee" in markdown_values


def test_replace_changes_student_top_pick() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run()

    app.sidebar.radio[0].set_value("Librarian").run()
    app.selectbox[1].set_value("STU-003").run()
    app.selectbox[2].set_value("BK-012").run()
    app.button[3].click().run()

    app.sidebar.radio[0].set_value("Student").run()
    app.selectbox[0].set_value("STU-003").run()

    markdown_values = [item.value for item in app.markdown]
    assert "## The Parker Inheritance" in markdown_values


def test_district_view_renders_metrics_and_sections() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run()

    app.sidebar.radio[0].set_value("District leader").run()

    metric_labels = [metric.label for metric in app.metric]
    markdown_values = [item.value for item in app.markdown]

    assert "Students exposed" in metric_labels
    assert "Exposure rate" in metric_labels
    assert "Approval rate" in metric_labels
    assert "Average checkout lift" in metric_labels
    assert "### School comparison" in markdown_values
    assert "### Recommendation quality signals" in markdown_values
    assert len(app.dataframe) >= 1