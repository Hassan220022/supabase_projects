from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_action_forms_are_async_dashboard_actions():
    detail = (ROOT / "supabase_provisioner/templates/detail.html").read_text()

    assert 'action="/projects/{{ project.slug }}/delete"' in detail
    assert detail.count("data-async-form") >= 5
    assert '<script src="/static/app.js"></script>' in detail


def test_async_script_prevents_raw_endpoint_navigation():
    script = (ROOT / "supabase_provisioner/static/app.js").read_text()

    assert "event.preventDefault()" in script
    assert "fetch(form.action" in script
    assert "history.pushState" in script
