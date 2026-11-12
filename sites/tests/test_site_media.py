"""Tests for site image and video media API endpoints."""

import os
import uuid

import pytest

from sites.models import Image, Page, Video
from sites.services.site import SiteService
from sites.tests.helpers import make_file, make_image, make_video

pytestmark = pytest.mark.django_db


def images_url(site_id):
    """Return the URL for a site's image collection."""
    return f"/api/v1/sites/{site_id}/images"


def image_url(site_id, image_id):
    """Return the URL for a specific site image."""
    return f"/api/v1/sites/{site_id}/images/{image_id}"


def videos_url(site_id):
    """Return the URL for a site's video collection."""
    return f"/api/v1/sites/{site_id}/videos"


def video_url(site_id, video_id):
    """Return the URL for a specific site video."""
    return f"/api/v1/sites/{site_id}/videos/{video_id}"


@pytest.fixture
def other_site(other_user, theme):
    """Create another user's site for ownership and isolation tests."""
    return SiteService.create(created_by=other_user, theme=theme, name="Other Site")


@pytest.fixture
def other_page(other_site):
    """Create a page belonging to another site."""
    return Page.objects.create(site=other_site, title="Elsewhere", page_type="about")


def create_image(site, page=None, name="pic.png", alt_text=""):
    """Create an image directly through the ORM."""
    return Image.objects.create(site=site, page=page, file=make_image(name), alt_text=alt_text)


def create_video(site, page=None, name="clip.mp4", title="clip", poster=None):
    """Create a video directly through the ORM."""
    return Video.objects.create(
        site=site, page=page, file=make_video(name), title=title, poster=poster
    )


def test_list_images_returns_all_unpaginated(auth_client, site):
    """Return all site images without applying pagination."""
    for index in range(12):
        create_image(site, name=f"pic{index}.png")

    response = auth_client.get(images_url(site.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 12


def test_list_images_only_from_this_site(auth_client, site, other_site, theme):
    """Return only images belonging to the requested site."""
    mine = create_image(site, name="mine.png")
    create_image(other_site, name="theirs.png")
    Image.objects.create(theme=theme, file=make_image("theme.png"))

    data = auth_client.get(images_url(site.id)).json()["data"]

    assert [item["id"] for item in data] == [str(mine.id)]


def test_list_images_filtered_by_page(auth_client, site, page):
    """Filter the site's images by the requested page."""
    on_page = create_image(site, page=page, name="on_page.png")
    create_image(site, name="site_level.png")

    everything = auth_client.get(images_url(site.id)).json()["data"]
    filtered = auth_client.get(images_url(site.id), {"page": str(page.id)}).json()["data"]

    assert len(everything) == 2
    assert [item["id"] for item in filtered] == [str(on_page.id)]
    assert filtered[0]["page"] == str(page.id)


def test_list_images_invalid_page_filter_rejected(auth_client, site):
    """Reject an invalid UUID supplied as the page filter."""
    response = auth_client.get(images_url(site.id), {"page": "not-a-uuid"})

    assert response.status_code == 400
    assert "page" in response.json()["errors"]


def test_list_images_unknown_site_returns_404(auth_client):
    """Return 404 when the requested site does not exist."""
    response = auth_client.get(images_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Site not found."


def test_list_images_requires_login(anon_client, site):
    """Require authentication when listing site images."""
    assert anon_client.get(images_url(site.id)).status_code in (401, 403)


def test_list_images_by_another_user_is_allowed(other_client, site):
    """Allow any authenticated user to read a site's media."""
    assert other_client.get(images_url(site.id)).status_code == 200


def test_upload_single_image(auth_client, site):
    """Upload one image and verify its metadata and stored file."""
    response = auth_client.post(
        images_url(site.id),
        {"files": [make_image("hero.png")], "alt_text": "A hero"},
        format="multipart",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["alt_text"] == "A hero"
    assert data[0]["width"] == 10
    assert data[0]["height"] == 10
    assert data[0]["size"] > 0
    assert data[0]["page"] is None

    image = Image.objects.get()
    assert image.site_id == site.id
    assert image.theme_id is None
    assert image.file.name.startswith(f"sites/{site.id}/images/")
    assert os.path.exists(image.file.path)


def test_upload_multiple_images(auth_client, site):
    """Upload multiple images in a single request."""
    files = [make_image("a.png"), make_image("b.png"), make_image("c.png")]
    response = auth_client.post(images_url(site.id), {"files": files}, format="multipart")

    assert response.status_code == 201
    assert len(response.json()["data"]) == 3
    assert Image.objects.filter(site=site).count() == 3


def test_upload_image_to_a_page(auth_client, site, page):
    """Associate an uploaded image with a page belonging to the site."""
    response = auth_client.post(
        images_url(site.id),
        {"files": [make_image("on_page.png")], "page": str(page.id)},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.json()["data"][0]["page"] == str(page.id)
    assert Image.objects.get().page_id == page.id


def test_upload_image_with_page_of_another_site_rejected(auth_client, site, other_page):
    """Reject an image upload targeting a page from another site."""
    response = auth_client.post(
        images_url(site.id),
        {"files": [make_image("x.png")], "page": str(other_page.id)},
        format="multipart",
    )

    assert response.status_code == 400
    assert "page" in response.json()["errors"]
    assert Image.objects.count() == 0


def test_upload_image_without_files_rejected(auth_client, site):
    """Reject an image upload request that does not include files."""
    response = auth_client.post(images_url(site.id), {"alt_text": "none"}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]


def test_upload_non_image_rejected(auth_client, site):
    """Reject a file that is not a supported image."""
    response = auth_client.post(
        images_url(site.id), {"files": [make_file("notes.txt")]}, format="multipart"
    )

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Image.objects.count() == 0


def test_upload_is_all_or_nothing(auth_client, site):
    """Reject the entire upload when one file in the batch is invalid."""
    files = [make_image("ok.png"), make_file("bad.txt")]
    response = auth_client.post(images_url(site.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert Image.objects.count() == 0


def test_upload_too_many_images_rejected(auth_client, site):
    """Reject an upload containing more images than the allowed limit."""
    files = [make_image(f"p{index}.png") for index in range(11)]
    response = auth_client.post(images_url(site.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Image.objects.count() == 0


def test_upload_image_by_non_owner_forbidden(other_client, site):
    """Prevent a user who does not own the site from uploading images."""
    response = other_client.post(
        images_url(site.id), {"files": [make_image("x.png")]}, format="multipart"
    )

    assert response.status_code == 403
    assert Image.objects.count() == 0


def test_upload_image_to_unknown_site_returns_404(auth_client):
    """Return 404 when uploading an image to a nonexistent site."""
    response = auth_client.post(
        images_url(uuid.uuid4()), {"files": [make_image("x.png")]}, format="multipart"
    )
    assert response.status_code == 404


def test_upload_image_requires_login(anon_client, site):
    """Require authentication when uploading images."""
    response = anon_client.post(
        images_url(site.id), {"files": [make_image("x.png")]}, format="multipart"
    )
    assert response.status_code in (401, 403)


def test_get_image(auth_client, site):
    """Return the requested image and its metadata."""
    image = create_image(site, alt_text="Logo")

    response = auth_client.get(image_url(site.id, image.id))

    assert response.status_code == 200
    assert response.json()["data"]["alt_text"] == "Logo"


def test_get_unknown_image_returns_404(auth_client, site):
    """Return 404 when the requested image does not exist."""
    response = auth_client.get(image_url(site.id, uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Image not found."


def test_get_image_of_another_site_returns_404(auth_client, site, other_site):
    """Prevent retrieving an image through a different site's route."""
    foreign = create_image(other_site)

    assert auth_client.get(image_url(site.id, foreign.id)).status_code == 404


def test_get_theme_image_through_site_route_returns_404(auth_client, site, theme):
    """Prevent retrieving a theme image through a site's media route."""
    theme_image = Image.objects.create(theme=theme, file=make_image("theme.png"))

    assert auth_client.get(image_url(site.id, theme_image.id)).status_code == 404


def test_patch_image_alt_text(auth_client, site):
    """Update an image's alternative text."""
    image = create_image(site, alt_text="old")

    response = auth_client.patch(
        image_url(site.id, image.id), {"alt_text": "new"}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json()["data"]["alt_text"] == "new"


def test_patch_image_replaces_file_and_deletes_old(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Replace an image file and delete the previous file after commit."""
    image = create_image(site, name="old.png")
    old_path = image.file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            image_url(site.id, image.id), {"file": make_image("new.png")}, format="multipart"
        )

    assert response.status_code == 200
    image.refresh_from_db()
    assert image.file.path != old_path
    assert os.path.exists(image.file.path)
    assert not os.path.exists(old_path)


def test_patch_image_with_bad_file_keeps_old_one(auth_client, site):
    """Reject an invalid replacement file without deleting the existing image."""
    image = create_image(site, name="keep.png")
    old_path = image.file.path

    response = auth_client.patch(
        image_url(site.id, image.id), {"file": make_file("bad.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "file" in response.json()["errors"]
    assert os.path.exists(old_path)


def test_patch_image_by_non_owner_forbidden(other_client, site):
    """Prevent a non-owner from modifying an image's metadata."""
    image = create_image(site, alt_text="mine")

    response = other_client.patch(
        image_url(site.id, image.id), {"alt_text": "hijacked"}, format="multipart"
    )

    assert response.status_code == 403
    image.refresh_from_db()
    assert image.alt_text == "mine"


def test_delete_image_removes_row_and_file(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Delete an image record and its stored file."""
    image = create_image(site)
    path = image.file.path
    assert os.path.exists(path)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(image_url(site.id, image.id))

    assert response.status_code == 200
    assert not Image.objects.filter(pk=image.pk).exists()
    assert not os.path.exists(path)


def test_delete_image_keeps_other_images(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Delete only the requested image and preserve other site images."""
    target = create_image(site, name="target.png")
    other = create_image(site, name="other.png")

    with django_capture_on_commit_callbacks(execute=True):
        auth_client.delete(image_url(site.id, target.id))

    assert Image.objects.filter(pk=other.pk).exists()
    assert os.path.exists(other.file.path)


def test_delete_image_by_non_owner_forbidden(other_client, site):
    """Prevent a non-owner from deleting an image."""
    image = create_image(site)

    response = other_client.delete(image_url(site.id, image.id))

    assert response.status_code == 403
    assert Image.objects.filter(pk=image.pk).exists()


def test_delete_image_of_another_site_returns_404(auth_client, site, other_site):
    """Prevent deleting an image through a different site's route."""
    foreign = create_image(other_site)

    response = auth_client.delete(image_url(site.id, foreign.id))

    assert response.status_code == 404
    assert Image.objects.filter(pk=foreign.pk).exists()


def test_deleted_image_is_gone(auth_client, site):
    """Return 404 when retrieving an image after it has been deleted."""
    image = create_image(site)
    auth_client.delete(image_url(site.id, image.id))

    assert auth_client.get(image_url(site.id, image.id)).status_code == 404


def test_list_videos_returns_all_unpaginated(auth_client, site):
    """Return all site videos without applying pagination."""
    for index in range(12):
        create_video(site, name=f"clip{index}.mp4", title=f"clip {index}")

    response = auth_client.get(videos_url(site.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 12


def test_list_videos_only_from_this_site(auth_client, site, other_site, theme):
    """Return only videos belonging to the requested site."""
    mine = create_video(site, name="mine.mp4")
    create_video(other_site, name="theirs.mp4")
    Video.objects.create(theme=theme, file=make_video("theme.mp4"))

    data = auth_client.get(videos_url(site.id)).json()["data"]

    assert [item["id"] for item in data] == [str(mine.id)]


def test_list_videos_filtered_by_page(auth_client, site, page):
    """Filter the site's videos by the requested page."""
    on_page = create_video(site, page=page, name="on_page.mp4")
    create_video(site, name="site_level.mp4")

    filtered = auth_client.get(videos_url(site.id), {"page": str(page.id)}).json()["data"]

    assert [item["id"] for item in filtered] == [str(on_page.id)]
    assert filtered[0]["page"] == str(page.id)


def test_list_videos_unknown_site_returns_404(auth_client):
    """Return 404 when listing videos for a nonexistent site."""
    assert auth_client.get(videos_url(uuid.uuid4())).status_code == 404


def test_list_videos_requires_login(anon_client, site):
    """Require authentication when listing site videos."""
    assert anon_client.get(videos_url(site.id)).status_code in (401, 403)


def test_upload_single_video(auth_client, site):
    """Upload one video and verify its metadata and stored file."""
    response = auth_client.post(
        videos_url(site.id), {"files": [make_video("intro clip.mp4")]}, format="multipart"
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "intro clip"
    assert data[0]["size"] > 0
    assert data[0]["page"] is None
    assert data[0]["duration"] is None

    video = Video.objects.get()
    assert video.site_id == site.id
    assert video.theme_id is None
    assert video.file.name.startswith(f"sites/{site.id}/videos/")
    assert os.path.exists(video.file.path)


def test_upload_multiple_videos(auth_client, site):
    """Upload multiple supported videos in a single request."""
    files = [make_video("a.mp4"), make_video("b.webm"), make_video("c.mov")]
    response = auth_client.post(videos_url(site.id), {"files": files}, format="multipart")

    assert response.status_code == 201
    assert len(response.json()["data"]) == 3
    assert Video.objects.filter(site=site).count() == 3


def test_upload_video_to_a_page(auth_client, site, page):
    """Associate an uploaded video with a page belonging to the site."""
    response = auth_client.post(
        videos_url(site.id),
        {"files": [make_video("on_page.mp4")], "page": str(page.id)},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.json()["data"][0]["page"] == str(page.id)


def test_upload_video_with_page_of_another_site_rejected(auth_client, site, other_page):
    """Reject a video upload targeting a page from another site."""
    response = auth_client.post(
        videos_url(site.id),
        {"files": [make_video("x.mp4")], "page": str(other_page.id)},
        format="multipart",
    )

    assert response.status_code == 400
    assert "page" in response.json()["errors"]
    assert Video.objects.count() == 0


def test_upload_video_without_files_rejected(auth_client, site):
    """Reject a video upload request that does not include files."""
    response = auth_client.post(videos_url(site.id), {}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]


def test_upload_unsupported_video_type_rejected(auth_client, site):
    """Reject a file with an unsupported video format."""
    response = auth_client.post(
        videos_url(site.id), {"files": [make_file("clip.avi")]}, format="multipart"
    )

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Video.objects.count() == 0


def test_upload_videos_is_all_or_nothing(auth_client, site):
    """Reject the entire video upload when one file in the batch is invalid."""
    files = [make_video("ok.mp4"), make_file("bad.txt")]
    response = auth_client.post(videos_url(site.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert Video.objects.count() == 0


def test_upload_too_many_videos_rejected(auth_client, site):
    """Reject an upload containing more videos than the allowed limit."""
    files = [make_video(f"v{index}.mp4") for index in range(6)]
    response = auth_client.post(videos_url(site.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Video.objects.count() == 0


def test_upload_video_by_non_owner_forbidden(other_client, site):
    """Prevent a user who does not own the site from uploading videos."""
    response = other_client.post(
        videos_url(site.id), {"files": [make_video("x.mp4")]}, format="multipart"
    )

    assert response.status_code == 403
    assert Video.objects.count() == 0


def test_upload_video_requires_login(anon_client, site):
    """Require authentication when uploading videos."""
    response = anon_client.post(
        videos_url(site.id), {"files": [make_video("x.mp4")]}, format="multipart"
    )
    assert response.status_code in (401, 403)


def test_get_video(auth_client, site):
    """Return the requested video and its metadata."""
    video = create_video(site, title="Intro")

    response = auth_client.get(video_url(site.id, video.id))

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Intro"


def test_get_unknown_video_returns_404(auth_client, site):
    """Return 404 when the requested video does not exist."""
    response = auth_client.get(video_url(site.id, uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Video not found."


def test_get_video_of_another_site_returns_404(auth_client, site, other_site):
    """Prevent retrieving a video through a different site's route."""
    foreign = create_video(other_site)

    assert auth_client.get(video_url(site.id, foreign.id)).status_code == 404


def test_patch_video_title(auth_client, site):
    """Update a video's title."""
    video = create_video(site, title="old")

    response = auth_client.patch(
        video_url(site.id, video.id), {"title": "new"}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "new"


def test_patch_video_adds_poster(auth_client, site):
    """Add a poster image to a video."""
    video = create_video(site)

    response = auth_client.patch(
        video_url(site.id, video.id), {"poster": make_image("poster.png")}, format="multipart"
    )

    assert response.status_code == 200
    video.refresh_from_db()
    assert video.poster
    assert os.path.exists(video.poster.path)


def test_patch_video_replaces_poster_and_deletes_old(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Replace a video's poster and delete the previous file after commit."""
    video = create_video(site, poster=make_image("old_poster.png"))
    old_path = video.poster.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            video_url(site.id, video.id),
            {"poster": make_image("new_poster.png")},
            format="multipart",
        )

    assert response.status_code == 200
    video.refresh_from_db()
    assert video.poster.path != old_path
    assert os.path.exists(video.poster.path)
    assert not os.path.exists(old_path)


def test_patch_video_clears_poster_and_deletes_file(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Clear a video's poster and delete the previously stored file."""
    video = create_video(site, poster=make_image("poster.png"))
    old_path = video.poster.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            video_url(site.id, video.id), {"poster": ""}, format="multipart"
        )

    assert response.status_code == 200
    video.refresh_from_db()
    assert not video.poster
    assert not os.path.exists(old_path)


def test_patch_video_replaces_file_deletes_old_and_resets_duration(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Replace a video's file, delete the old file, and reset its duration."""
    video = create_video(site, name="old.mp4")
    video.duration = 30
    video.save()
    old_path = video.file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            video_url(site.id, video.id), {"file": make_video("new.mp4")}, format="multipart"
        )

    assert response.status_code == 200
    video.refresh_from_db()
    assert video.file.path != old_path
    assert os.path.exists(video.file.path)
    assert not os.path.exists(old_path)
    assert video.duration is None


def test_patch_video_with_bad_file_keeps_old_one(auth_client, site):
    """Reject an invalid replacement video without deleting the existing file."""
    video = create_video(site, name="keep.mp4")
    old_path = video.file.path

    response = auth_client.patch(
        video_url(site.id, video.id), {"file": make_file("bad.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "file" in response.json()["errors"]
    assert os.path.exists(old_path)


def test_patch_video_with_bad_poster_rejected(auth_client, site):
    """Reject an invalid file supplied as a video poster."""
    video = create_video(site)

    response = auth_client.patch(
        video_url(site.id, video.id), {"poster": make_file("poster.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "poster" in response.json()["errors"]


def test_patch_video_by_non_owner_forbidden(other_client, site):
    """Prevent a non-owner from modifying a video's metadata."""
    video = create_video(site, title="mine")

    response = other_client.patch(
        video_url(site.id, video.id), {"title": "hijacked"}, format="multipart"
    )

    assert response.status_code == 403
    video.refresh_from_db()
    assert video.title == "mine"


def test_delete_video_removes_row_file_and_poster(
    auth_client, site, django_capture_on_commit_callbacks
):
    """Delete a video record, its stored video file, and its poster."""
    video = create_video(site, poster=make_image("poster.png"))
    paths = [video.file.path, video.poster.path]
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(video_url(site.id, video.id))

    assert response.status_code == 200
    assert not Video.objects.filter(pk=video.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_video_without_poster(auth_client, site, django_capture_on_commit_callbacks):
    """Delete a video that does not have a poster image."""
    video = create_video(site)
    path = video.file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(video_url(site.id, video.id))

    assert response.status_code == 200
    assert not os.path.exists(path)


def test_delete_video_by_non_owner_forbidden(other_client, site):
    """Prevent a non-owner from deleting a video."""
    video = create_video(site)

    response = other_client.delete(video_url(site.id, video.id))

    assert response.status_code == 403
    assert Video.objects.filter(pk=video.pk).exists()


def test_delete_video_of_another_site_returns_404(auth_client, site, other_site):
    """Prevent deleting a video through a different site's route."""
    foreign = create_video(other_site)

    response = auth_client.delete(video_url(site.id, foreign.id))

    assert response.status_code == 404
    assert Video.objects.filter(pk=foreign.pk).exists()


def test_deleted_video_is_gone(auth_client, site):
    """Return 404 when retrieving a video after it has been deleted."""
    video = create_video(site)
    auth_client.delete(video_url(site.id, video.id))

    assert auth_client.get(video_url(site.id, video.id)).status_code == 404