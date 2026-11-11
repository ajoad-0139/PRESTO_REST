# sites/tests/test_themes.py
import os
import uuid

import pytest

from sites.models import Site, Theme
from sites.services.site import SiteService
from sites.tests.helpers import make_file

URL = "/api/v1/themes"

pytestmark = pytest.mark.django_db


def detail_url(theme_id):
    return f"{URL}/{theme_id}"


# POST /api/v1/themes
def test_create_theme(auth_client, theme_payload):
    response = auth_client.post(URL, theme_payload(), format="multipart")

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "modern-business"
    assert body["data"]["is_active"] is True
    assert Theme.objects.count() == 1


def test_create_theme_requires_login(anon_client, theme_payload):
    response = anon_client.post(URL, theme_payload(), format="multipart")
    assert response.status_code in (401, 403)
    assert response.json()["success"] is False


def test_create_duplicate_theme_rejected(auth_client, theme_payload):
    assert auth_client.post(URL, theme_payload(), format="multipart").status_code == 201

    response = auth_client.post(URL, theme_payload(name="modern business"), format="multipart")

    assert response.status_code == 409
    assert response.json()["success"] is False
    assert Theme.objects.count() == 1


def test_create_theme_short_name_rejected(auth_client, theme_payload):
    response = auth_client.post(URL, theme_payload(name="ab"), format="multipart")

    assert response.status_code == 400
    assert "name" in response.json()["errors"]


def test_create_theme_bad_file_type_rejected(auth_client, theme_payload):
    bad = theme_payload(header=make_file("header.txt"))
    response = auth_client.post(URL, bad, format="multipart")

    assert response.status_code == 400
    assert "header" in response.json()["errors"]


# GET /api/v1/themes
def test_list_themes_is_paginated(auth_client, theme):
    response = auth_client.get(URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pagination"]["count"] == 1
    assert data["items"][0]["id"] == str(theme.id)


def test_list_filters_by_active(auth_client, theme):
    theme.is_active = False
    theme.save()

    assert auth_client.get(URL, {"is_active": "true"}).json()["data"]["items"] == []
    assert len(auth_client.get(URL, {"is_active": "false"}).json()["data"]["items"]) == 1


def test_list_does_not_include_media(auth_client, theme):
    item = auth_client.get(URL).json()["data"]["items"][0]
    assert "images" not in item
    assert "videos" not in item


# GET /api/v1/themes/<id>
def test_get_theme(auth_client, theme):
    response = auth_client.get(detail_url(theme.id))

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Modern Business"


def test_get_unknown_theme_returns_404(auth_client):
    response = auth_client.get(detail_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Theme not found."


# PATCH /api/v1/themes/<id>
def test_patch_theme_renames_and_updates_slug(auth_client, theme):
    response = auth_client.patch(
        detail_url(theme.id), {"name": "Renamed Theme"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Renamed Theme"
    assert data["slug"] == "renamed-theme"
    assert data["is_active"] is True      # not reset by a partial update


def test_patch_theme_by_non_owner_forbidden(other_client, theme):
    response = other_client.patch(
        detail_url(theme.id), {"name": "Hijacked"}, format="multipart"
    )
    assert response.status_code == 403


def test_patch_theme_to_existing_name_rejected(auth_client, theme, theme_payload):
    auth_client.post(URL, theme_payload(name="Second Theme"), format="multipart")

    response = auth_client.patch(
        detail_url(theme.id), {"name": "second theme"}, format="multipart"
    )
    assert response.status_code == 409


# DELETE /api/v1/themes/<id>
def test_delete_theme_removes_row_and_files(
    auth_client, theme, django_capture_on_commit_callbacks
):
    path = theme.thumbnail.path
    assert os.path.exists(path)

    # on_commit callbacks only run when asked to inside a test
    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(detail_url(theme.id))

    assert response.status_code == 200
    assert not Theme.objects.filter(pk=theme.pk).exists()
    assert not os.path.exists(path)


def test_delete_theme_by_non_owner_forbidden(other_client, theme):
    response = other_client.delete(detail_url(theme.id))

    assert response.status_code == 403
    assert Theme.objects.filter(pk=theme.pk).exists()


def test_delete_theme_in_use_is_blocked(auth_client, owner, theme):
    SiteService.create(created_by=owner, theme=theme, name="Uses Theme")

    response = auth_client.delete(detail_url(theme.id))

    assert response.status_code == 409
    assert Theme.objects.filter(pk=theme.pk).exists()
    assert Site.objects.count() == 1