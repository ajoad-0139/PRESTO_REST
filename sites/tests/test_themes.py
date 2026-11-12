"""Tests for theme API endpoints."""

import os
import uuid

import pytest

from sites.models import Site, Theme
from sites.services.site import SiteService
from sites.tests.helpers import make_file

URL = "/api/v1/themes"

pytestmark = pytest.mark.django_db


def detail_url(theme_id):
    """Build the URL for a specific theme."""
    return f"{URL}/{theme_id}"


def test_create_theme(auth_client, theme_payload):
    """Verify that an authenticated user can create a theme successfully."""
    response = auth_client.post(URL, theme_payload(), format="multipart")

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "modern-business"
    assert body["data"]["is_active"] is True
    assert Theme.objects.count() == 1


def test_create_theme_requires_login(anon_client, theme_payload):
    """Verify that unauthenticated users cannot create themes."""
    response = anon_client.post(URL, theme_payload(), format="multipart")
    assert response.status_code in (401, 403)
    assert response.json()["success"] is False


def test_create_duplicate_theme_rejected(auth_client, theme_payload):
    """Verify that a user cannot create themes with duplicate names."""
    assert auth_client.post(URL, theme_payload(), format="multipart").status_code == 201

    response = auth_client.post(URL, theme_payload(name="modern business"), format="multipart")

    assert response.status_code == 409
    assert response.json()["success"] is False
    assert Theme.objects.count() == 1


def test_create_theme_short_name_rejected(auth_client, theme_payload):
    """Verify that creating a theme with a name that is too short is rejected."""
    response = auth_client.post(URL, theme_payload(name="ab"), format="multipart")

    assert response.status_code == 400
    assert "name" in response.json()["errors"]


def test_create_theme_bad_file_type_rejected(auth_client, theme_payload):
    """Verify that uploading an unsupported file type for the theme header is rejected."""
    bad = theme_payload(header=make_file("header.txt"))
    response = auth_client.post(URL, bad, format="multipart")

    assert response.status_code == 400
    assert "header" in response.json()["errors"]


def test_list_themes_is_paginated(auth_client, theme):
    """Verify that the theme list uses pagination and includes the user's theme."""
    response = auth_client.get(URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pagination"]["count"] == 1
    assert data["items"][0]["id"] == str(theme.id)


def test_list_filters_by_active(auth_client, theme):
    """Verify that the theme list can be filtered by its active status."""
    theme.is_active = False
    theme.save()

    assert auth_client.get(URL, {"is_active": "true"}).json()["data"]["items"] == []
    assert len(auth_client.get(URL, {"is_active": "false"}).json()["data"]["items"]) == 1


def test_list_does_not_include_media(auth_client, theme):
    """Verify that theme list responses do not include image or video collections."""
    item = auth_client.get(URL).json()["data"]["items"][0]
    assert "images" not in item
    assert "videos" not in item


def test_get_theme(auth_client, theme):
    """Verify that retrieving a theme returns its details."""
    response = auth_client.get(detail_url(theme.id))

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Modern Business"


def test_get_unknown_theme_returns_404(auth_client):
    """Verify that requesting an unknown theme returns 404."""
    response = auth_client.get(detail_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Theme not found."


def test_patch_theme_renames_and_updates_slug(auth_client, theme):
    """Verify that renaming a theme updates its slug without resetting other fields."""
    response = auth_client.patch(
        detail_url(theme.id), {"name": "Renamed Theme"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Renamed Theme"
    assert data["slug"] == "renamed-theme"
    assert data["is_active"] is True


def test_patch_theme_by_non_owner_forbidden(other_client, theme):
    """Verify that a non-owner cannot update another user's theme."""
    response = other_client.patch(
        detail_url(theme.id), {"name": "Hijacked"}, format="multipart"
    )
    assert response.status_code == 403


def test_patch_theme_to_existing_name_rejected(auth_client, theme, theme_payload):
    """Verify that a theme cannot be renamed to another existing theme's name."""
    auth_client.post(URL, theme_payload(name="Second Theme"), format="multipart")

    response = auth_client.patch(
        detail_url(theme.id), {"name": "second theme"}, format="multipart"
    )
    assert response.status_code == 409


def test_delete_theme_removes_row_and_files(
    auth_client, theme, django_capture_on_commit_callbacks
):
    """Verify that deleting a theme removes its database record and stored thumbnail."""
    path = theme.thumbnail.path
    assert os.path.exists(path)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(detail_url(theme.id))

    assert response.status_code == 200
    assert not Theme.objects.filter(pk=theme.pk).exists()
    assert not os.path.exists(path)


def test_delete_theme_by_non_owner_forbidden(other_client, theme):
    """Verify that a non-owner cannot delete another user's theme."""
    response = other_client.delete(detail_url(theme.id))

    assert response.status_code == 403
    assert Theme.objects.filter(pk=theme.pk).exists()


def test_delete_theme_in_use_is_blocked(auth_client, owner, theme):
    """Verify that a theme used by a site cannot be deleted."""
    SiteService.create(created_by=owner, theme=theme, name="Uses Theme")

    response = auth_client.delete(detail_url(theme.id))

    assert response.status_code == 409
    assert Theme.objects.filter(pk=theme.pk).exists()
    assert Site.objects.count() == 1