# Reading Lift POC Behavior Test Report

Date: 2026-04-02

## Launch and Browser

- Streamlit app launched locally on `http://localhost:8502`
- App opened in the VS Code simple browser
- Live HTTP check returned `200 OK`

## Test Method

- UI behavior was validated with Streamlit's `AppTest` harness against `reading_lift_poc/app.py`
- This approach exercises the real Streamlit widget tree and session state without depending on unsupported simple-browser DOM tooling
- A browser-only QA subagent initially reported a stale startup error; that result was superseded after direct HTTP verification and repeatable AppTest runs

## Scenarios Executed

1. Student view renders the hero recommendation, explanation, secondary list, and student action buttons
2. Librarian view renders school selection, student selection, queue snapshot, recommendation detail, and action buttons
3. Librarian `Approve` action updates the current state and writes an audit entry
4. Librarian `Pin to top` changes the student-facing top recommendation for the same student
5. Librarian `Replace` changes the student-facing top recommendation with a valid in-band replacement title
6. District leader view renders headline metrics plus comparison and quality sections

## Result Summary

- Status: Pass
- Automated behavior tests passed: 5
- Startup blocker fixed during validation: `reading_lift_poc` import path resolution when launched via `streamlit run`
- Non-blocking cleanup completed: replaced deprecated `use_container_width` usage with `width="stretch"`

## Observed Behavior

- Student view defaulted to a working recommendation state with `Scythe` as the top pick for the seeded student
- Librarian actions persisted in session state and immediately affected rendered UI state
- Pinning `Refugee` for `Maya Patel` moved it to the top of the student page
- Replacing Maya's recommendation with `The Parker Inheritance` surfaced that title as the new hero recommendation
- District leader view rendered summary metrics, school comparison data, and recommendation quality metrics without runtime errors

## Follow-Up Notes

- The simple browser opened correctly, but direct DOM inspection is not available through this tool path unless the browser chat tools setting is enabled
- The repeatable behavior suite now lives in `tests/test_streamlit_behavior.py`