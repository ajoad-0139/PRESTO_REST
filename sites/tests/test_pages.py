# sites/tests/test_pages.py
import os
import uuid

import pytest

from sites.models import Image, Page, Site, Video
from sites.services.site import SiteService
from sites.tests.helpers import (
    make_css, make_file, make_html, make_image, make_js, make_video,
)

pytestmark = pytest.mark.django_db


# ---------- urls ----------

def pages_url(site_id):
    return f"/api/v1/sites/{site_id}/pages"


def page_url(site_id, page_id):
    return f"/api/v1/sites/{site_id}/pages/{page_id}"


# ---------- fixtures and builders ----------

@pytest.fixture
def other_site(other_user, theme):
    return SiteService.create(created_by=other_user, theme=theme, name="Other Site")


def create_page(site, title, page_type="general", **extra):
    # html_file and css_file are required on a page, so give them defaults
    extra.setdefault("html_file", make_html("page.html"))
    extra.setdefault("css_file", make_css("page.css"))
    return Page.objects.create(site=site, title=title, page_type=page_type, **extra)


def create_page_with_files(site, title="With Files"):
    return create_page(
        site, title, page_type="landing",
        html_file=make_html("old.html"), css_file=make_css("old.css"),
        js_file=make_js("old.js"), og_image=make_image("old_og.png"),
    )


def paths_of(page):
    return [page.html_file.path, page.css_file.path, page.js_file.path, page.og_image.path]


# =====================================================================
# POST /api/v1/sites/<id>/pages
# =====================================================================

def page_payload(**overrides):
    """Smallest valid request: title, page_type and the two required files."""
    data = {
        "title": "Contact",
        "page_type": "contact",
        "html_file": make_html("contact.html"),
        "css_file": make_css("contact.css"),
    }
    data.update(overrides)
    return data


def test_create_minimal_page(auth_client, site):
    response = auth_client.post(pages_url(site.id), page_payload(), format="multipart")

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["title"] == "Contact"
    assert data["slug"] == "contact"
    assert data["page_type"] == "contact"
    assert data["site"] == str(site.id)
    assert data["no_index"] is False
    assert data["html_file"]
    assert data["css_file"]
    assert data["js_file"] is None
    assert data["og_image"] is None


def test_create_page_with_all_files(auth_client, site):
    payload = page_payload(
        title="Landing", page_type="landing",
        canonical_url="https://example.com/landing",
        meta_title="Landing | Example", meta_description="A landing page.",
        og_title="Landing", og_description="Share text.", no_index="true",
        html_file=make_html("landing.html"), css_file=make_css("landing.css"),
        js_file=make_js("landing.js"), og_image=make_image("share.png"),
    )
    response = auth_client.post(pages_url(site.id), payload, format="multipart")

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert data["no_index"] is True
    assert data["canonical_url"] == "https://example.com/landing"
    for field in ("html_file", "css_file", "js_file", "og_image"):
        assert data[field]

    page = Page.objects.get()
    prefix = f"sites/{site.id}/pages/{page.id}"
    assert page.html_file.name.startswith(f"{prefix}/html/")
    assert page.css_file.name.startswith(f"{prefix}/css/")
    assert page.js_file.name.startswith(f"{prefix}/js/")
    assert page.og_image.name.startswith(f"{prefix}/images/")
    assert all(os.path.exists(path) for path in paths_of(page))


def test_create_page_slug_comes_from_title(auth_client, site):
    response = auth_client.post(
        pages_url(site.id), page_payload(title="About Our Team", page_type="about"),
        format="multipart",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["data"]["slug"] == "about-our-team"


def test_create_page_normalises_title_and_type(auth_client, site):
    response = auth_client.post(
        pages_url(site.id), page_payload(title="  Pricing  ", page_type="  PRICING "),
        format="multipart",
    )

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert data["title"] == "Pricing"
    assert data["page_type"] == "pricing"


def test_create_duplicate_title_rejected(auth_client, site, page):
    # the `page` fixture is already titled "About Us"
    response = auth_client.post(
        pages_url(site.id), page_payload(title="about us", page_type="about"), format="multipart"
    )

    assert response.status_code == 409, response.json()
    assert response.json()["success"] is False
    assert Page.objects.filter(site=site).count() == 1


def test_create_same_title_in_another_site_allowed(other_client, other_site, page):
    response = other_client.post(
        pages_url(other_site.id), page_payload(title="About Us", page_type="about"),
        format="multipart",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["data"]["slug"] == "about-us"      # the same slug in another site is fine


def test_create_page_with_same_slug_rejected(auth_client, site, page):
    # "About Us!" is a different title, but it slugifies to the same "about-us"
    response = auth_client.post(
        pages_url(site.id), page_payload(title="About Us!", page_type="about"), format="multipart"
    )

    assert response.status_code == 409, response.json()
    assert Page.objects.filter(site=site).count() == 1


def test_create_page_with_same_slug_in_another_site_allowed(other_client, other_site, page):
    # the `page` fixture lives in `site`; a different site may reuse the same slug
    response = other_client.post(
        pages_url(other_site.id), page_payload(title="About Us!", page_type="about"),
        format="multipart",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["data"]["slug"] == "about-us"


@pytest.mark.parametrize("missing", ["title", "page_type", "html_file", "css_file"])
def test_create_page_missing_required_field(auth_client, site, missing):
    payload = page_payload()
    del payload[missing]

    response = auth_client.post(pages_url(site.id), payload, format="multipart")

    assert response.status_code == 400, response.json()
    assert list(response.json()["errors"]) == [missing]
    assert Page.objects.count() == 0


def test_create_page_short_title_rejected(auth_client, site):
    response = auth_client.post(
        pages_url(site.id), page_payload(title="A", page_type="about"), format="multipart"
    )

    assert response.status_code == 400, response.json()
    assert "title" in response.json()["errors"]


@pytest.mark.parametrize("field, length", [
    ("meta_title", 71), ("meta_description", 161), ("og_title", 96), ("og_description", 201),
])
def test_create_page_text_limits(auth_client, site, field, length):
    payload = page_payload(**{field: "x" * length})

    response = auth_client.post(pages_url(site.id), payload, format="multipart")

    assert response.status_code == 400, response.json()
    assert list(response.json()["errors"]) == [field]
    assert Page.objects.count() == 0


@pytest.mark.parametrize("field, filename", [
    ("html_file", "page.txt"), ("css_file", "style.js"),
    ("js_file", "app.css"), ("og_image", "share.pdf"),
])
def test_create_page_bad_file_type_rejected(auth_client, site, field, filename):
    payload = page_payload(**{field: make_file(filename)})

    response = auth_client.post(pages_url(site.id), payload, format="multipart")

    assert response.status_code == 400, response.json()
    assert list(response.json()["errors"]) == [field]
    assert Page.objects.count() == 0


def test_create_page_by_non_owner_forbidden(other_client, site):
    response = other_client.post(pages_url(site.id), page_payload(), format="multipart")

    assert response.status_code == 403, response.json()
    assert Page.objects.count() == 0


def test_staff_can_create_page_in_any_site(staff_client, site):
    response = staff_client.post(pages_url(site.id), page_payload(), format="multipart")

    assert response.status_code == 201, response.json()


def test_create_page_unknown_site_returns_404(auth_client):
    response = auth_client.post(pages_url(uuid.uuid4()), page_payload(), format="multipart")

    assert response.status_code == 404, response.json()
    assert response.json()["message"] == "Site not found."


def test_create_page_requires_login(anon_client, site):
    response = anon_client.post(pages_url(site.id), page_payload(), format="multipart")

    assert response.status_code in (401, 403), response.json()
    assert Page.objects.count() == 0


# =====================================================================
# GET /api/v1/sites/<id>/pages
# =====================================================================

def test_list_pages_returns_all_unpaginated(auth_client, site):
    for index in range(12):
        create_page(site, f"Page number {index}")

    response = auth_client.get(pages_url(site.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 12


def test_list_pages_empty_site(auth_client, site):
    response = auth_client.get(pages_url(site.id))

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_pages_only_from_this_site(auth_client, site, other_site, page):
    create_page(other_site, "Foreign Page")

    data = auth_client.get(pages_url(site.id)).json()["data"]

    assert [item["id"] for item in data] == [str(page.id)]


def test_list_pages_newest_first(auth_client, site):
    first = create_page(site, "First Page")
    second = create_page(site, "Second Page")

    data = auth_client.get(pages_url(site.id)).json()["data"]

    assert [item["id"] for item in data] == [str(second.id), str(first.id)]


def test_list_pages_filter_by_type(auth_client, site, page):
    create_page(site, "Contact", page_type="contact")

    data = auth_client.get(pages_url(site.id), {"page_type": "CONTACT"}).json()["data"]

    assert [item["title"] for item in data] == ["Contact"]


def test_list_pages_search_by_title(auth_client, site, page):
    create_page(site, "Contact", page_type="contact")

    assert [p["title"] for p in auth_client.get(pages_url(site.id), {"search": "abo"}).json()["data"]] == ["About Us"]
    assert auth_client.get(pages_url(site.id), {"search": "zzz"}).json()["data"] == []


def test_list_pages_filters_combined(auth_client, site, page):
    create_page(site, "About Team", page_type="team")

    data = auth_client.get(pages_url(site.id), {"page_type": "about", "search": "about"}).json()["data"]

    assert [item["title"] for item in data] == ["About Us"]


def test_list_pages_unknown_site_returns_404(auth_client):
    assert auth_client.get(pages_url(uuid.uuid4())).status_code == 404


def test_list_pages_requires_login(anon_client, site):
    assert anon_client.get(pages_url(site.id)).status_code in (401, 403)


def test_list_pages_by_another_user_is_allowed(other_client, site, page):
    # current rule: any logged-in user can read a site's pages
    assert other_client.get(pages_url(site.id)).status_code == 200


# =====================================================================
# GET /api/v1/sites/<id>/pages/<page_id>
# =====================================================================

def test_get_page(auth_client, site, page):
    response = auth_client.get(page_url(site.id, page.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(page.id)
    assert data["title"] == "About Us"
    assert data["slug"] == "about-us"
    assert data["site"] == str(site.id)


def test_get_unknown_page_returns_404(auth_client, site):
    response = auth_client.get(page_url(site.id, uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Page not found."


def test_get_page_of_another_site_returns_404(auth_client, site, other_site):
    foreign = create_page(other_site, "Foreign Page")

    assert auth_client.get(page_url(site.id, foreign.id)).status_code == 404


def test_get_page_unknown_site_returns_404(auth_client, page):
    response = auth_client.get(page_url(uuid.uuid4(), page.id))

    assert response.status_code == 404
    assert response.json()["message"] == "Site not found."


def test_get_page_requires_login(anon_client, site, page):
    assert anon_client.get(page_url(site.id, page.id)).status_code in (401, 403)


# =====================================================================
# PATCH /api/v1/sites/<id>/pages/<page_id>
# =====================================================================

def test_patch_page_updates_only_sent_fields(auth_client, site, page):
    page.no_index = True
    page.save()

    response = auth_client.patch(
        page_url(site.id, page.id), {"meta_title": "New meta"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["meta_title"] == "New meta"
    assert data["title"] == "About Us"
    assert data["no_index"] is True       # a missing form boolean must not reset it


def test_patch_page_rename_changes_slug(auth_client, site, page):
    response = auth_client.patch(
        page_url(site.id, page.id), {"title": "About Our Team"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "About Our Team"
    assert data["slug"] == "about-our-team"


def test_patch_page_same_title_keeps_slug(auth_client, site, page):
    response = auth_client.patch(
        page_url(site.id, page.id), {"title": "About Us"}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json()["data"]["slug"] == "about-us"


def test_patch_page_title_case_change_is_allowed(auth_client, site, page):
    response = auth_client.patch(
        page_url(site.id, page.id), {"title": "about us"}, format="multipart"
    )

    assert response.status_code == 200      # it only matches itself
    assert response.json()["data"]["title"] == "about us"


def test_patch_page_to_existing_title_rejected(auth_client, site, page):
    other = create_page(site, "Contact")

    response = auth_client.patch(
        page_url(site.id, other.id), {"title": "about us"}, format="multipart"
    )

    assert response.status_code == 409
    other.refresh_from_db()
    assert other.title == "Contact"


def test_patch_page_to_title_used_in_another_site_allowed(auth_client, site, other_site, page):
    create_page(other_site, "Pricing")

    response = auth_client.patch(
        page_url(site.id, page.id), {"title": "Pricing"}, format="multipart"
    )

    assert response.status_code == 200


def test_patch_page_rename_to_same_slug_rejected(auth_client, site, page):
    other = create_page(site, "Contact")

    # a different title that still slugifies to "about-us", which `page` already uses
    response = auth_client.patch(
        page_url(site.id, other.id), {"title": "About Us!"}, format="multipart"
    )

    assert response.status_code == 409
    other.refresh_from_db()
    assert other.title == "Contact"
    assert other.slug == "contact"


def test_patch_page_title_with_its_own_slug_allowed(auth_client, site, page):
    # "About Us!" slugifies to this page's own slug, so it only matches itself
    response = auth_client.patch(
        page_url(site.id, page.id), {"title": "About Us!"}, format="multipart"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "About Us!"
    assert data["slug"] == "about-us"


def test_patch_page_type_is_normalised(auth_client, site, page):
    response = auth_client.patch(
        page_url(site.id, page.id), {"page_type": "  CONTACT "}, format="multipart"
    )

    assert response.json()["data"]["page_type"] == "contact"


def test_patch_page_short_title_rejected(auth_client, site, page):
    response = auth_client.patch(
        page_url(site.id, page.id), {"title": "A"}, format="multipart"
    )

    assert response.status_code == 400
    assert "title" in response.json()["errors"]


def test_patch_page_cannot_change_slug_or_site(auth_client, site, other_site, page):
    response = auth_client.patch(
        page_url(site.id, page.id),
        {"slug": "hacked", "site": str(other_site.id)},
        format="multipart",
    )

    assert response.status_code == 200
    page.refresh_from_db()
    assert page.slug == "about-us"
    assert page.site_id == site.id


def test_patch_page_replaces_file_and_deletes_old(
    auth_client, site, django_capture_on_commit_callbacks
):
    page = create_page_with_files(site)
    old_path = page.html_file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            page_url(site.id, page.id), {"html_file": make_html("new.html")}, format="multipart"
        )

    assert response.status_code == 200
    page.refresh_from_db()
    assert page.html_file.path != old_path
    assert os.path.exists(page.html_file.path)
    assert not os.path.exists(old_path)


def test_patch_page_adds_first_file_without_deleting_anything(auth_client, site, page):
    # the page has no js file yet, so there is nothing old to delete
    html_path = page.html_file.path

    response = auth_client.patch(
        page_url(site.id, page.id), {"js_file": make_js("first.js")}, format="multipart"
    )

    assert response.status_code == 200
    page.refresh_from_db()
    assert page.js_file
    assert os.path.exists(page.js_file.path)
    assert os.path.exists(html_path)


def test_patch_page_clears_file_and_deletes_it(
    auth_client, site, django_capture_on_commit_callbacks
):
    page = create_page_with_files(site)
    old_path = page.js_file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            page_url(site.id, page.id), {"js_file": ""}, format="multipart"
        )

    assert response.status_code == 200
    page.refresh_from_db()
    assert not page.js_file
    assert not os.path.exists(old_path)
    assert os.path.exists(page.html_file.path)       # the other files are untouched


def test_patch_page_with_bad_file_keeps_old_one(auth_client, site):
    page = create_page_with_files(site)
    old_path = page.html_file.path

    response = auth_client.patch(
        page_url(site.id, page.id), {"html_file": make_file("bad.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "html_file" in response.json()["errors"]
    assert os.path.exists(old_path)


def test_patch_page_by_non_owner_forbidden(other_client, site, page):
    response = other_client.patch(
        page_url(site.id, page.id), {"title": "Hijacked"}, format="multipart"
    )

    assert response.status_code == 403
    page.refresh_from_db()
    assert page.title == "About Us"


def test_patch_unknown_page_returns_404(auth_client, site):
    response = auth_client.patch(
        page_url(site.id, uuid.uuid4()), {"title": "Ghost"}, format="multipart"
    )

    assert response.status_code == 404


def test_patch_page_of_another_site_returns_404(auth_client, site, other_site):
    foreign = create_page(other_site, "Foreign Page")

    response = auth_client.patch(
        page_url(site.id, foreign.id), {"title": "Taken Over"}, format="multipart"
    )

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.title == "Foreign Page"


def test_patch_page_requires_login(anon_client, site, page):
    response = anon_client.patch(
        page_url(site.id, page.id), {"title": "Anon"}, format="multipart"
    )
    assert response.status_code in (401, 403)


# =====================================================================
# DELETE /api/v1/sites/<id>/pages/<page_id>
# =====================================================================

def test_delete_page_removes_row_and_files(
    auth_client, site, django_capture_on_commit_callbacks
):
    page = create_page_with_files(site)
    paths = paths_of(page)
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(page_url(site.id, page.id))

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert not Page.objects.filter(pk=page.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_page_with_required_files_only(
    auth_client, site, page, django_capture_on_commit_callbacks
):
    paths = [page.html_file.path, page.css_file.path]
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(page_url(site.id, page.id))

    assert response.status_code == 200
    assert not Page.objects.filter(pk=page.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_page_removes_its_images_and_videos(
    auth_client, site, page, django_capture_on_commit_callbacks
):
    image = Image.objects.create(site=site, page=page, file=make_image("on_page.png"))
    video = Video.objects.create(
        site=site, page=page, file=make_video("on_page.mp4"), poster=make_image("poster.png")
    )
    paths = [image.file.path, video.file.path, video.poster.path]
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(page_url(site.id, page.id))

    assert response.status_code == 200
    assert not Image.objects.filter(pk=image.pk).exists()
    assert not Video.objects.filter(pk=video.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_page_keeps_site_level_media_and_other_pages(
    auth_client, site, page, django_capture_on_commit_callbacks
):
    site_image = Image.objects.create(site=site, file=make_image("site_level.png"))
    other_page = create_page(site, "Other Page")
    other_image = Image.objects.create(site=site, page=other_page, file=make_image("other.png"))

    with django_capture_on_commit_callbacks(execute=True):
        auth_client.delete(page_url(site.id, page.id))

    assert Site.objects.filter(pk=site.pk).exists()
    assert Page.objects.filter(pk=other_page.pk).exists()
    assert Image.objects.filter(pk=site_image.pk).exists()
    assert os.path.exists(site_image.file.path)
    assert Image.objects.filter(pk=other_image.pk).exists()
    assert os.path.exists(other_image.file.path)


def test_delete_page_by_non_owner_forbidden(other_client, site, page):
    response = other_client.delete(page_url(site.id, page.id))

    assert response.status_code == 403
    assert Page.objects.filter(pk=page.pk).exists()


def test_staff_can_delete_any_page(staff_client, site, page):
    response = staff_client.delete(page_url(site.id, page.id))

    assert response.status_code == 200
    assert not Page.objects.filter(pk=page.pk).exists()


def test_delete_unknown_page_returns_404(auth_client, site):
    assert auth_client.delete(page_url(site.id, uuid.uuid4())).status_code == 404


def test_delete_page_of_another_site_returns_404(auth_client, site, other_site):
    foreign = create_page(other_site, "Foreign Page")

    response = auth_client.delete(page_url(site.id, foreign.id))

    assert response.status_code == 404
    assert Page.objects.filter(pk=foreign.pk).exists()


def test_deleted_page_is_gone(auth_client, site, page):
    auth_client.delete(page_url(site.id, page.id))

    assert auth_client.get(page_url(site.id, page.id)).status_code == 404
    assert auth_client.delete(page_url(site.id, page.id)).status_code == 404


def test_delete_page_requires_login(anon_client, site, page):
    assert anon_client.delete(page_url(site.id, page.id)).status_code in (401, 403)
    assert Page.objects.filter(pk=page.pk).exists()