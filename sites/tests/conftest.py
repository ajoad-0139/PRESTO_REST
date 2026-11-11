# sites/tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from sites.services.page import PageService
from sites.services.site import SiteService
from sites.services.theme import ThemeService
from sites.tests.helpers import make_css, make_html, make_image


# ---------- storage: never write into your real media/ folder ----------

@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


# ---------- users and clients ----------

def _create_user(username, **extra):
    # if your user model logs in by email, change this to create_user(email=..., password=...)
    return get_user_model().objects.create_user(username=username, password="pass12345", **extra)


@pytest.fixture
def owner(db):
    return _create_user("owner")


@pytest.fixture
def other_user(db):
    return _create_user("other")


@pytest.fixture
def staff_user(db):
    return _create_user("staff", is_staff=True)


def _client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)   # skips login and CSRF
    return client


@pytest.fixture
def anon_client():
    return _client_for()


@pytest.fixture
def auth_client(owner):
    return _client_for(owner)


@pytest.fixture
def other_client(other_user):
    return _client_for(other_user)


@pytest.fixture
def staff_client(staff_user):
    return _client_for(staff_user)


# ---------- data builders ----------

@pytest.fixture
def theme_payload():
    """Call it for a fresh dict each time, because uploaded files are consumed once."""
    def build(**overrides):
        data = {
            "name": "Modern Business",
            "language": "en",
            "thumbnail": make_image("thumb.png"),
            "header": make_html("header.html"),
            "footer": make_html("footer.html"),
            "body": make_html("body.html"),
            "css_file": make_css("index.css"),
        }
        data.update(overrides)
        return data
    return build


@pytest.fixture
def theme(owner, theme_payload):
    return ThemeService.create(created_by=owner, **theme_payload())


@pytest.fixture
def site(owner, theme):
    return SiteService.create(created_by=owner, theme=theme, name="My Site")


@pytest.fixture
def page(owner, site):
    return PageService.create(
        site_id=site.id, user=owner, title="About Us", page_type="about"
    )