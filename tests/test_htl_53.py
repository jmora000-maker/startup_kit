"""HTL-53: The Fact Review page should start with all expanders collapsed.

Today, the fact-category sections on Fact Review default to collapsed (expanded=False) on page load.
"""

from datetime import date
from pathlib import Path
from streamlit.testing.v1 import AppTest

from src.core.models import ProjectStartupCharter, StartupKitBaseline
from src.review_storage.local import LocalReviewStorage
from src.review_ui import facts as review

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


def test_fact_review_category_expanders_render_collapsed_by_default(tmp_path, monkeypatch):
    """HTL-53: Fact Review page fact-category expanders must all default to collapsed (expanded=False)."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="HTL-53 Collapsed Expander Test",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Acme Corp"),
    )
    categories = review.build_fact_categories(review.prepare_review_baseline(baseline))
    category_titles = [c.title for c in categories]

    run_id = storage.create_run(
        project_name="HTL-53 Collapsed Expander Test",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Find expanders matching each fact category
    cat_expanders = [e for e in at.expander if e.label in category_titles]
    assert len(cat_expanders) == len(category_titles)
    assert len(cat_expanders) == 7

    # Verify every single category expander is collapsed (expanded=False)
    for exp in cat_expanders:
        assert not exp.proto.expanded, f"Expander '{exp.label}' was unexpectedly expanded by default"


def test_fact_review_demo_fixture_category_expanders_collapsed_by_default():
    """HTL-53: Demo fixture mode on Fact Review also starts with all category expanders collapsed."""
    baseline = review.load_baseline(review.FIXTURE_BASELINE_PATH)
    categories = review.build_fact_categories(review.prepare_review_baseline(baseline))
    category_titles = [c.title for c in categories]

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").select(review.DEMO_FIXTURE_OPTION).run()
    assert not at.exception

    cat_expanders = [e for e in at.expander if e.label in category_titles]
    assert len(cat_expanders) == len(category_titles)
    assert len(cat_expanders) == 7

    for exp in cat_expanders:
        assert not exp.proto.expanded, f"Demo expander '{exp.label}' was unexpectedly expanded by default"


def test_fact_review_all_expanders_on_page_are_collapsed_by_default(tmp_path, monkeypatch):
    """HTL-53: Verify that every expander on the Fact Review page (fact categories and generation gate)
    is collapsed by default.
    """
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="HTL-53 All Expanders Test",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Acme Corp"),
    )
    run_id = storage.create_run(
        project_name="HTL-53 All Expanders Test",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Total expanders = 7 categories + 1 generation access expander = 8 expanders
    assert len(at.expander) == 8
    for exp in at.expander:
        assert not exp.proto.expanded, f"Expander '{exp.label}' was unexpectedly expanded by default"
