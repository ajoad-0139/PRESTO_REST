"""Tests for site API endpoints."""

import os
import uuid

import pytest

from sites.models import Site, Theme
from sites.services.site import SiteService
from sites.tests.helpers import make_image

URL = "/api/v1/sites"

pytestmark = pytest.mark.django_db


def detail_url(site_id):
    """Return the URL for a specific site."""
    return f"{URL}/{site_id}"


def create_payload(theme, **overrides):
    """Build a site creation payload with optional overridden fields."""
    data = {"name": "My First Site", "theme": str(theme.id)}
    data.update(overrides)
    return data


def test_create_site(auth_client, owner, theme):
    """Create a site with the supplied theme and verify its default values."""
    response = auth_client.post(URL, create_payload(theme), format="multipart")

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "draft"
    assert data["slug"] == "my-first-site"
    assert data["theme"] == str(theme.id)
    assert data["created_by"] == owner.pk


def test_create_site_copies_theme_files(auth_client, theme):
    """Copy the theme's template files into site-owned storage."""
    auth_client.post(URL, create_payload(theme), format="multipart")

    site = Site.objects.get()
    for field in ("header", "footer", "body", "css_file"):
        site_file = getattr(site, field)
        theme_file = getattr(theme, field)
        assert site_file.name != theme_file.name
        assert os.path.exists(site_file.path)
        assert site_file.read() == theme_file.read()
    assert not site.js_file


def test_create_site_with_optional_files(auth_client, theme):
    """Create a site with optional favicon and Open Graph image files."""
    payload = create_payload(
        theme, favicon=make_image("fav.png"), og_image=make_image("og.png")
    )
    response = auth_client.post(URL, payload, format="multipart")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["favicon"]
    assert data["og_image"]


def test_create_site_requires_login(anon_client, theme):
    """Require authentication when creating a site."""
    response = anon_client.post(URL, create_payload(theme), format="multipart")

    assert response.status_code in (401, 403)
    assert response.json()["success"] is False


def test_create_site_requires_theme(auth_client):
    """Reject site creation when no theme is provided."""
    response = auth_client.post(URL, {"name": "No Theme"}, format="multipart")

    assert response.status_code == 400
    assert "theme" in response.json()["errors"]


def test_create_site_unknown_theme_rejected(auth_client):
    """Reject site creation when the supplied theme does not exist."""
    payload = {"name": "Ghost Theme Site", "theme": str(uuid.uuid4())}
    response = auth_client.post(URL, payload, format="multipart")

    assert response.status_code == 400
    assert "theme" in response.json()["errors"]


def test_create_site_inactive_theme_rejected(auth_client, theme):
    """Reject site creation when the selected theme is inactive."""
    theme.is_active = False
    theme.save()

    response = auth_client.post(URL, create_payload(theme), format="multipart")

    assert response.status_code == 400
    assert "theme" in response.json()["errors"]


def test_create_site_short_name_rejected(auth_client, theme):
    """Reject site creation when the name is shorter than the allowed length."""
    response = auth_client.post(URL, create_payload(theme, name="ab"), format="multipart")

    assert response.status_code == 400
    assert "name" in response.json()["errors"]


def test_create_site_unsupported_language_rejected(auth_client, theme):
    """Reject site creation when an unsupported language is supplied."""
    response = auth_client.post(URL, create_payload(theme, language="xx"), format="multipart")

    assert response.status_code == 400
    assert "language" in response.json()["errors"]


def test_create_site_domain_is_lowercased(auth_client, theme):
    """Normalize the published domain to lowercase during site creation."""
    payload = create_payload(theme, published_domain="  Example.COM ")
    response = auth_client.post(URL, payload, format="multipart")

    assert response.status_code == 201
    assert response.json()["data"]["published_domain"] == "example.com"


def test_create_site_duplicate_domain_rejected(auth_client, owner, theme):
    """Reject site creation when the published domain is already in use."""
    SiteService.create(
        created_by=owner, theme=theme, name="First", published_domain="example.com"
    )

    payload = create_payload(theme, published_domain="example.com")
    response = auth_client.post(URL, payload, format="multipart")

    assert response.status_code == 400
    assert "published_domain" in response.json()["errors"]


def test_create_two_sites_without_domain_allowed(auth_client, theme):
    """Allow multiple sites without a published domain."""
    first = auth_client.post(
        URL, create_payload(theme, name="First Site"), format="multipart"
    )
    second = auth_client.post(
        URL, create_payload(theme, name="Second Site"), format="multipart"
    )

    assert first.status_code == 201
    assert second.status_code == 201


def test_list_sites_is_paginated(auth_client, site):
    """Return the authenticated user's sites in a paginated response."""
    response = auth_client.get(URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pagination"]["count"] == 1
    assert data["items"][0]["id"] == str(site.id)


def test_list_shows_only_own_sites(auth_client, other_user, theme, site):
    """Return only sites owned by the authenticated user."""
    SiteService.create(created_by=other_user, theme=theme, name="Other Site")

    items = auth_client.get(URL).json()["data"]["items"]

    assert [item["id"] for item in items] == [str(site.id)]


def test_list_filters_by_status(auth_client, site):
    """Filter the authenticated user's sites by status."""
    site.status = Site.Status.PUBLISHED
    site.save()

    assert len(auth_client.get(URL, {"status": "published"}).json()["data"]["items"]) == 1
    assert auth_client.get(URL, {"status": "draft"}).json()["data"]["items"] == []


def test_list_invalid_status_rejected(auth_client, site):
    """Reject an unsupported site status filter."""
    response = auth_client.get(URL, {"status": "bogus"})

    assert response.status_code == 400
    assert "status" in response.json()["errors"]


def test_list_search_by_name(auth_client, site):
    """Filter the site list by a search term in the site name."""
    assert len(auth_client.get(URL, {"search": "my"}).json()["data"]["items"]) == 1
    assert auth_client.get(URL, {"search": "zzz"}).json()["data"]["items"] == []


def test_list_requires_login(anon_client):
    """Require authentication when listing sites."""
    assert anon_client.get(URL).status_code in (401, 403)


def test_get_site(auth_client, site):
    """Return the requested site's details."""
    response = auth_client.get(detail_url(site.id))

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "My Site"


def test_get_unknown_site_returns_404(auth_client):
    """Return 404 when the requested site does not exist."""
    response = auth_client.get(detail_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Site not found."


def test_get_site_by_another_user_is_allowed(other_client, site):
    """Allow any authenticated user to view a site."""
    assert other_client.get(detail_url(site.id)).status_code == 200


def test_patch_site_updates_only_sent_fields(auth_client, site):
    """Update supplied fields without resetting omitted boolean fields."""
    site.no_index = True
    site.save()

    response = auth_client.patch(
        detail_url(site.id), {"description": "Updated text"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["description"] == "Updated text"
    assert data["no_index"] is True


def test_patch_site_rename_changes_slug(auth_client, site):
    """Update the site's slug when its name changes."""
    response = auth_client.patch(
        detail_url(site.id), {"name": "Brand New Name"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Brand New Name"
    assert data["slug"] == "brand-new-name"


def test_patch_site_keeps_own_slug_when_name_unchanged(auth_client, site):
    """Keep the existing slug when the site name remains unchanged."""
    response = auth_client.patch(
        detail_url(site.id), {"name": "My Site", "description": "x"}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json()["data"]["slug"] == "my-site"


def test_publish_without_domain_rejected(auth_client, site):
    """Prevent publishing a site without a published domain."""
    response = auth_client.patch(
        detail_url(site.id), {"status": "published"}, format="multipart"
    )

    assert response.status_code == 400
    assert "published_domain" in response.json()["errors"]
    site.refresh_from_db()
    assert site.status == Site.Status.DRAFT


def test_publish_with_domain_in_same_request(auth_client, site):
    """Allow publishing when a domain is supplied in the same request."""
    response = auth_client.patch(
        detail_url(site.id),
        {"status": "published", "published_domain": "Live-Site.com"},
        format="multipart",
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "published"
    assert data["published_domain"] == "live-site.com"


def test_patch_site_to_taken_domain_rejected(auth_client, owner, theme, site):
    """Reject updating a site with a domain already assigned to another site."""
    SiteService.create(
        created_by=owner, theme=theme, name="Other", published_domain="taken.com"
    )

    response = auth_client.patch(
        detail_url(site.id), {"published_domain": "taken.com"}, format="multipart"
    )

    assert response.status_code == 400
    assert "published_domain" in response.json()["errors"]


def test_patch_site_keeping_own_domain_allowed(auth_client, owner, theme):
    """Allow a site to retain its own published domain."""
    mine = SiteService.create(
        created_by=owner, theme=theme, name="Mine", published_domain="mine.com"
    )

    response = auth_client.patch(
        detail_url(mine.id), {"published_domain": "mine.com"}, format="multipart"
    )

    assert response.status_code == 200


def test_patch_site_by_non_owner_forbidden(other_client, site):
    """Prevent users who do not own a site from modifying it."""
    response = other_client.patch(
        detail_url(site.id), {"description": "Hijacked"}, format="multipart"
    )

    assert response.status_code == 403
    site.refresh_from_db()
    assert site.description != "Hijacked"


def test_patch_unknown_site_returns_404(auth_client):
    """Return 404 when attempting to update a nonexistent site."""
    response = auth_client.patch(
        detail_url(uuid.uuid4()), {"description": "x"}, format="multipart"
    )
    assert response.status_code == 404


def test_patch_replaces_favicon_and_deletes_old_file(
    auth_client, owner, theme, django_capture_on_commit_callbacks
):
    """Replace a site's favicon and delete the previous file after commit."""
    site = SiteService.create(
        created_by=owner, theme=theme, name="Icon Site", favicon=make_image("old.png")
    )
    old_path = site.favicon.path
    assert os.path.exists(old_path)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            detail_url(site.id), {"favicon": make_image("new.png")}, format="multipart"
        )

    assert response.status_code == 200
    site.refresh_from_db()
    assert os.path.exists(site.favicon.path)
    assert site.favicon.path != old_path
    assert not os.path.exists(old_path)


def test_patch_clears_favicon_and_deletes_file(
    auth_client, owner, theme, django_capture_on_commit_callbacks
):
    """Clear a site's favicon and delete its previously stored file."""
    site = SiteService.create(
        created_by=owner, theme=theme, name="Icon Site", favicon=make_image("old.png")
    )
    old_path = site.favicon.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            detail_url(site.id), {"favicon": ""}, format="multipart"
        )

    assert response.status_code == 200
    site.refresh_from_db()
    assert not site.favicon
    assert not os.path.exists(old_path)


def test_delete_site_removes_row_and_files(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Delete a site record and its copied template files."""
    paths = [site.header.path, site.footer.path, site.body.path, site.css_file.path]
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(detail_url(site.id))

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert not Site.objects.filter(pk=site.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_site_keeps_the_theme_and_its_files(
    auth_client, site, theme, django_capture_on_commit_callbacks
):
    """Delete a site without deleting its shared theme or theme files."""
    with django_capture_on_commit_callbacks(execute=True):
        auth_client.delete(detail_url(site.id))

    assert Theme.objects.filter(pk=theme.pk).exists()
    assert os.path.exists(theme.header.path)
    assert os.path.exists(theme.css_file.path)


def test_deleted_site_is_gone(auth_client, site):
    """Return 404 when retrieving or deleting a site after deletion."""
    auth_client.delete(detail_url(site.id))

    assert auth_client.get(detail_url(site.id)).status_code == 404
    assert auth_client.delete(detail_url(site.id)).status_code == 404


def test_delete_site_by_non_owner_forbidden(other_client, site):
    """Prevent users who do not own a site from deleting it."""
    response = other_client.delete(detail_url(site.id))

    assert response.status_code == 403
    assert Site.objects.filter(pk=site.pk).exists()


def test_staff_can_delete_any_site(staff_client, site):
    """Allow staff users to delete sites they do not own."""
    response = staff_client.delete(detail_url(site.id))

    assert response.status_code == 200
    assert not Site.objects.filter(pk=site.pk).exists()


def test_delete_site_requires_login(anon_client, site):
    """Require authentication when deleting a site."""
    assert anon_client.delete(detail_url(site.id)).status_code in (401, 403)
    assert Site.objects.filter(pk=site.pk).exists()