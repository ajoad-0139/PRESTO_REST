import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from sites.services.page import PageService
from sites.services.site import SiteService
from sites.services.theme import ThemeService
from sites.tests.helpers import make_css, make_html, make_image


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """
    Use a temporary media directory for each test.

    Prevents test uploads from being written to the project's actual
    media directory.
    """
    settings.MEDIA_ROOT = tmp_path


def _create_user(username, **extra):
    """
    Create a test user with the given username and additional attributes.

    Args:
        username: Username for the new user.
        **extra: Additional user model fields.

    Returns:
        User: The newly created user.
    """
    return get_user_model().objects.create_user(
        username=username,
        password="pass12345",
        **extra
    )


@pytest.fixture
def owner(db):
    """
    Create and return the primary user who owns test resources.
    """
    return _create_user("owner")


@pytest.fixture
def other_user(db):
    """
    Create and return a second user for ownership and permission tests.
    """
    return _create_user("other")


@pytest.fixture
def staff_user(db):
    """
    Create and return a staff user for permission tests.
    """
    return _create_user("staff", is_staff=True)


def _client_for(user=None):
    """
    Create an API client and optionally authenticate it as a user.

    Uses force authentication to bypass the login process and CSRF checks.

    Args:
        user: User to authenticate as. Defaults to None.

    Returns:
        APIClient: Configured test API client.
    """
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


@pytest.fixture
def anon_client():
    """
    Create and return an unauthenticated API client.
    """
    return _client_for()


@pytest.fixture
def auth_client(owner):
    """
    Create and return an API client authenticated as the owner.
    """
    return _client_for(owner)


@pytest.fixture
def other_client(other_user):
    """
    Create and return an API client authenticated as another user.
    """
    return _client_for(other_user)


@pytest.fixture
def staff_client(staff_user):
    """
    Create and return an API client authenticated as a staff user.
    """
    return _client_for(staff_user)


@pytest.fixture
def theme_payload():
    """
    Return a factory for generating fresh theme creation data.

    A new dictionary and fresh uploaded files are created on each call
    because uploaded files are consumed during request processing.

    Returns:
        function: A factory that accepts optional field overrides and
            returns a theme creation payload.
    """
    def build(**overrides):
        """
        Build a theme payload with optional field overrides.

        Args:
            **overrides: Theme fields that replace the default values.

        Returns:
            dict: Theme creation data with fresh uploaded files.
        """
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
    """
    Create and return a theme owned by the primary test user.

    Uses ThemeService to create the theme with the default payload.
    """
    return ThemeService.create(created_by=owner, **theme_payload())


@pytest.fixture
def site(owner, theme):
    """
    Create and return a site owned by the primary test user.

    Associates the site with the theme fixture.
    """
    return SiteService.create(created_by=owner, theme=theme, name="My Site")


@pytest.fixture
def page(owner, site):
    """
    Create and return a page associated with the site fixture.

    Supplies the required HTML and CSS files during page creation.
    """
    return PageService.create(
        site_id=site.id,
        user=owner,
        title="About Us",
        page_type="about",
        html_file=make_html("about.html"),
        css_file=make_css("about.css"),
    )
