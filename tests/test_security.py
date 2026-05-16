import pytest

from supabase_provisioner.security import compose_project_name, validate_slug


def test_validate_slug_accepts_safe_names():
    assert validate_slug("my-app1") == "my-app1"
    assert compose_project_name("my-app1") == "sb_my_app1"


@pytest.mark.parametrize("slug", ["A", "1app", "app_", "app--x", "app.", "a" * 42])
def test_validate_slug_rejects_unsafe_names(slug):
    with pytest.raises(ValueError):
        validate_slug(slug)
