# sites/tests/test_theme_media.py
import os
import uuid

import pytest

from sites.models import Image, Theme, Video
from sites.services.theme import ThemeService
from sites.tests.helpers import make_file, make_image, make_video

pytestmark = pytest.mark.django_db


# ---------- urls ----------

def images_url(theme_id):
    return f"/api/v1/themes/{theme_id}/images"


def image_url(theme_id, image_id):
    return f"/api/v1/themes/{theme_id}/images/{image_id}"


def videos_url(theme_id):
    return f"/api/v1/themes/{theme_id}/videos"


def video_url(theme_id, video_id):
    return f"/api/v1/themes/{theme_id}/videos/{video_id}"


# ---------- fixtures and builders (ORM only, so they don't depend on the services) ----------

@pytest.fixture
def other_theme(other_user, theme_payload):
    return ThemeService.create(
        created_by=other_user, **theme_payload(name="Other Theme")
    )


def create_image(theme, name="pic.png", alt_text=""):
    return Image.objects.create(theme=theme, file=make_image(name), alt_text=alt_text)


def create_video(theme, name="clip.mp4", title="clip", poster=None):
    return Video.objects.create(theme=theme, file=make_video(name), title=title, poster=poster)


# =====================================================================
# IMAGES
# =====================================================================

# GET /api/v1/themes/<id>/images
def test_list_images_returns_all_unpaginated(auth_client, theme):
    for index in range(12):                       # more than one page of 10
        create_image(theme, name=f"pic{index}.png")

    response = auth_client.get(images_url(theme.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 12


def test_list_images_empty_theme(auth_client, theme):
    response = auth_client.get(images_url(theme.id))

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_images_only_from_this_theme(auth_client, theme, other_theme, site):
    mine = create_image(theme, name="mine.png")
    create_image(other_theme, name="theirs.png")
    Image.objects.create(site=site, file=make_image("site.png"))

    data = auth_client.get(images_url(theme.id)).json()["data"]

    assert [item["id"] for item in data] == [str(mine.id)]


def test_list_images_unknown_theme_returns_404(auth_client):
    response = auth_client.get(images_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Theme not found."


def test_list_images_requires_login(anon_client, theme):
    assert anon_client.get(images_url(theme.id)).status_code in (401, 403)


def test_list_images_by_another_user_is_allowed(other_client, theme):
    # current rule: any logged-in user can read a theme's media
    assert other_client.get(images_url(theme.id)).status_code == 200


# POST /api/v1/themes/<id>/images
def test_upload_single_image(auth_client, theme):
    response = auth_client.post(
        images_url(theme.id),
        {"files": [make_image("hero.png")], "alt_text": "A hero"},
        format="multipart",
    )

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["alt_text"] == "A hero"
    assert data[0]["width"] == 10
    assert data[0]["height"] == 10
    assert data[0]["size"] > 0

    image = Image.objects.get()
    assert image.theme_id == theme.id
    assert image.site_id is None
    assert image.page_id is None
    assert image.file.name.startswith(f"themes/{theme.id}/images/")
    assert os.path.exists(image.file.path)


def test_upload_multiple_images(auth_client, theme):
    files = [make_image("a.png"), make_image("b.png"), make_image("c.png")]
    response = auth_client.post(images_url(theme.id), {"files": files}, format="multipart")

    assert response.status_code == 201, response.json()
    assert len(response.json()["data"]) == 3
    assert Image.objects.filter(theme=theme).count() == 3


def test_upload_images_share_the_alt_text(auth_client, theme):
    files = [make_image("a.png"), make_image("b.png")]
    response = auth_client.post(
        images_url(theme.id), {"files": files, "alt_text": "Shared"}, format="multipart"
    )

    assert [item["alt_text"] for item in response.json()["data"]] == ["Shared", "Shared"]


def test_upload_image_without_files_rejected(auth_client, theme):
    response = auth_client.post(images_url(theme.id), {"alt_text": "none"}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]


def test_upload_non_image_rejected(auth_client, theme):
    response = auth_client.post(
        images_url(theme.id), {"files": [make_file("notes.txt")]}, format="multipart"
    )

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Image.objects.count() == 0


def test_upload_is_all_or_nothing(auth_client, theme):
    files = [make_image("ok.png"), make_file("bad.txt")]
    response = auth_client.post(images_url(theme.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert Image.objects.count() == 0


def test_upload_too_many_images_rejected(auth_client, theme):
    files = [make_image(f"p{index}.png") for index in range(11)]    # the limit is 10
    response = auth_client.post(images_url(theme.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Image.objects.count() == 0


def test_upload_image_by_non_owner_forbidden(other_client, theme):
    response = other_client.post(
        images_url(theme.id), {"files": [make_image("x.png")]}, format="multipart"
    )

    assert response.status_code == 403
    assert Image.objects.count() == 0


def test_staff_can_upload_image_to_any_theme(staff_client, theme):
    response = staff_client.post(
        images_url(theme.id), {"files": [make_image("x.png")]}, format="multipart"
    )

    assert response.status_code == 201, response.json()


def test_upload_image_to_unknown_theme_returns_404(auth_client):
    response = auth_client.post(
        images_url(uuid.uuid4()), {"files": [make_image("x.png")]}, format="multipart"
    )

    assert response.status_code == 404


def test_upload_image_requires_login(anon_client, theme):
    response = anon_client.post(
        images_url(theme.id), {"files": [make_image("x.png")]}, format="multipart"
    )

    assert response.status_code in (401, 403)
    assert Image.objects.count() == 0


# GET /api/v1/themes/<id>/images/<image_id>
def test_get_image(auth_client, theme):
    image = create_image(theme, alt_text="Logo")

    response = auth_client.get(image_url(theme.id, image.id))

    assert response.status_code == 200
    assert response.json()["data"]["alt_text"] == "Logo"


def test_get_unknown_image_returns_404(auth_client, theme):
    response = auth_client.get(image_url(theme.id, uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Image not found."


def test_get_image_under_unknown_theme_returns_404(auth_client, theme):
    image = create_image(theme)

    response = auth_client.get(image_url(uuid.uuid4(), image.id))

    assert response.status_code == 404
    assert response.json()["message"] == "Theme not found."


def test_get_image_of_another_theme_returns_404(auth_client, theme, other_theme):
    foreign = create_image(other_theme)

    assert auth_client.get(image_url(theme.id, foreign.id)).status_code == 404


def test_get_site_image_through_theme_route_returns_404(auth_client, theme, site):
    site_image = Image.objects.create(site=site, file=make_image("site.png"))

    assert auth_client.get(image_url(theme.id, site_image.id)).status_code == 404


# PATCH /api/v1/themes/<id>/images/<image_id>
def test_patch_image_alt_text(auth_client, theme):
    image = create_image(theme, alt_text="old")

    response = auth_client.patch(
        image_url(theme.id, image.id), {"alt_text": "new"}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json()["data"]["alt_text"] == "new"


def test_patch_image_replaces_file_and_deletes_old(
    auth_client, theme, django_capture_on_commit_callbacks
):
    image = create_image(theme, name="old.png")
    old_path = image.file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            image_url(theme.id, image.id), {"file": make_image("new.png")}, format="multipart"
        )

    assert response.status_code == 200
    image.refresh_from_db()
    assert image.file.path != old_path
    assert os.path.exists(image.file.path)
    assert not os.path.exists(old_path)


def test_patch_image_with_bad_file_keeps_old_one(auth_client, theme):
    image = create_image(theme, name="keep.png")
    old_path = image.file.path

    response = auth_client.patch(
        image_url(theme.id, image.id), {"file": make_file("bad.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "file" in response.json()["errors"]
    assert os.path.exists(old_path)


def test_patch_image_by_non_owner_forbidden(other_client, theme):
    image = create_image(theme, alt_text="mine")

    response = other_client.patch(
        image_url(theme.id, image.id), {"alt_text": "hijacked"}, format="multipart"
    )

    assert response.status_code == 403
    image.refresh_from_db()
    assert image.alt_text == "mine"


def test_patch_image_of_another_theme_returns_404(auth_client, theme, other_theme):
    foreign = create_image(other_theme, alt_text="theirs")

    response = auth_client.patch(
        image_url(theme.id, foreign.id), {"alt_text": "taken"}, format="multipart"
    )

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.alt_text == "theirs"


# DELETE /api/v1/themes/<id>/images/<image_id>
def test_delete_image_removes_row_and_file(
    auth_client, theme, django_capture_on_commit_callbacks
):
    image = create_image(theme)
    path = image.file.path
    assert os.path.exists(path)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(image_url(theme.id, image.id))

    assert response.status_code == 200
    assert not Image.objects.filter(pk=image.pk).exists()
    assert not os.path.exists(path)


def test_delete_image_keeps_other_images(
    auth_client, theme, django_capture_on_commit_callbacks
):
    target = create_image(theme, name="target.png")
    other = create_image(theme, name="other.png")

    with django_capture_on_commit_callbacks(execute=True):
        auth_client.delete(image_url(theme.id, target.id))

    assert Image.objects.filter(pk=other.pk).exists()
    assert os.path.exists(other.file.path)


def test_delete_image_by_non_owner_forbidden(other_client, theme):
    image = create_image(theme)

    response = other_client.delete(image_url(theme.id, image.id))

    assert response.status_code == 403
    assert Image.objects.filter(pk=image.pk).exists()


def test_staff_can_delete_any_theme_image(staff_client, theme):
    image = create_image(theme)

    response = staff_client.delete(image_url(theme.id, image.id))

    assert response.status_code == 200
    assert not Image.objects.filter(pk=image.pk).exists()


def test_delete_image_of_another_theme_returns_404(auth_client, theme, other_theme):
    foreign = create_image(other_theme)

    response = auth_client.delete(image_url(theme.id, foreign.id))

    assert response.status_code == 404
    assert Image.objects.filter(pk=foreign.pk).exists()


def test_deleted_image_is_gone(auth_client, theme):
    image = create_image(theme)
    auth_client.delete(image_url(theme.id, image.id))

    assert auth_client.get(image_url(theme.id, image.id)).status_code == 404


def test_delete_image_requires_login(anon_client, theme):
    image = create_image(theme)

    assert anon_client.delete(image_url(theme.id, image.id)).status_code in (401, 403)
    assert Image.objects.filter(pk=image.pk).exists()


# =====================================================================
# VIDEOS
# =====================================================================

# GET /api/v1/themes/<id>/videos
def test_list_videos_returns_all_unpaginated(auth_client, theme):
    for index in range(12):
        create_video(theme, name=f"clip{index}.mp4", title=f"clip {index}")

    response = auth_client.get(videos_url(theme.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 12


def test_list_videos_empty_theme(auth_client, theme):
    response = auth_client.get(videos_url(theme.id))

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_videos_only_from_this_theme(auth_client, theme, other_theme, site):
    mine = create_video(theme, name="mine.mp4")
    create_video(other_theme, name="theirs.mp4")
    Video.objects.create(site=site, file=make_video("site.mp4"))

    data = auth_client.get(videos_url(theme.id)).json()["data"]

    assert [item["id"] for item in data] == [str(mine.id)]


def test_list_videos_unknown_theme_returns_404(auth_client):
    response = auth_client.get(videos_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Theme not found."


def test_list_videos_requires_login(anon_client, theme):
    assert anon_client.get(videos_url(theme.id)).status_code in (401, 403)


# POST /api/v1/themes/<id>/videos
def test_upload_single_video(auth_client, theme):
    response = auth_client.post(
        videos_url(theme.id), {"files": [make_video("intro clip.mp4")]}, format="multipart"
    )

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "intro clip"          # defaults to the file name
    assert data[0]["size"] > 0
    assert data[0]["duration"] is None

    video = Video.objects.get()
    assert video.theme_id == theme.id
    assert video.site_id is None
    assert video.page_id is None
    assert video.file.name.startswith(f"themes/{theme.id}/videos/")
    assert os.path.exists(video.file.path)


def test_upload_multiple_videos(auth_client, theme):
    files = [make_video("a.mp4"), make_video("b.webm"), make_video("c.mov")]
    response = auth_client.post(videos_url(theme.id), {"files": files}, format="multipart")

    assert response.status_code == 201, response.json()
    assert len(response.json()["data"]) == 3
    assert Video.objects.filter(theme=theme).count() == 3


def test_upload_video_without_files_rejected(auth_client, theme):
    response = auth_client.post(videos_url(theme.id), {}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]


def test_upload_unsupported_video_type_rejected(auth_client, theme):
    response = auth_client.post(
        videos_url(theme.id), {"files": [make_file("clip.avi")]}, format="multipart"
    )

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Video.objects.count() == 0


def test_upload_videos_is_all_or_nothing(auth_client, theme):
    files = [make_video("ok.mp4"), make_file("bad.txt")]
    response = auth_client.post(videos_url(theme.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert Video.objects.count() == 0


def test_upload_too_many_videos_rejected(auth_client, theme):
    files = [make_video(f"v{index}.mp4") for index in range(6)]     # the limit is 5
    response = auth_client.post(videos_url(theme.id), {"files": files}, format="multipart")

    assert response.status_code == 400
    assert "files" in response.json()["errors"]
    assert Video.objects.count() == 0


def test_upload_video_by_non_owner_forbidden(other_client, theme):
    response = other_client.post(
        videos_url(theme.id), {"files": [make_video("x.mp4")]}, format="multipart"
    )

    assert response.status_code == 403
    assert Video.objects.count() == 0


def test_staff_can_upload_video_to_any_theme(staff_client, theme):
    response = staff_client.post(
        videos_url(theme.id), {"files": [make_video("x.mp4")]}, format="multipart"
    )

    assert response.status_code == 201, response.json()


def test_upload_video_to_unknown_theme_returns_404(auth_client):
    response = auth_client.post(
        videos_url(uuid.uuid4()), {"files": [make_video("x.mp4")]}, format="multipart"
    )

    assert response.status_code == 404


def test_upload_video_requires_login(anon_client, theme):
    response = anon_client.post(
        videos_url(theme.id), {"files": [make_video("x.mp4")]}, format="multipart"
    )

    assert response.status_code in (401, 403)
    assert Video.objects.count() == 0


# GET /api/v1/themes/<id>/videos/<video_id>
def test_get_video(auth_client, theme):
    video = create_video(theme, title="Intro")

    response = auth_client.get(video_url(theme.id, video.id))

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Intro"


def test_get_unknown_video_returns_404(auth_client, theme):
    response = auth_client.get(video_url(theme.id, uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["message"] == "Video not found."


def test_get_video_under_unknown_theme_returns_404(auth_client, theme):
    video = create_video(theme)

    response = auth_client.get(video_url(uuid.uuid4(), video.id))

    assert response.status_code == 404
    assert response.json()["message"] == "Theme not found."


def test_get_video_of_another_theme_returns_404(auth_client, theme, other_theme):
    foreign = create_video(other_theme)

    assert auth_client.get(video_url(theme.id, foreign.id)).status_code == 404


def test_get_site_video_through_theme_route_returns_404(auth_client, theme, site):
    site_video = Video.objects.create(site=site, file=make_video("site.mp4"))

    assert auth_client.get(video_url(theme.id, site_video.id)).status_code == 404


# PATCH /api/v1/themes/<id>/videos/<video_id>
def test_patch_video_title(auth_client, theme):
    video = create_video(theme, title="old")

    response = auth_client.patch(
        video_url(theme.id, video.id), {"title": "new"}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "new"


def test_patch_video_adds_poster(auth_client, theme):
    video = create_video(theme)

    response = auth_client.patch(
        video_url(theme.id, video.id), {"poster": make_image("poster.png")}, format="multipart"
    )

    assert response.status_code == 200
    video.refresh_from_db()
    assert video.poster
    assert os.path.exists(video.poster.path)


def test_patch_video_replaces_poster_and_deletes_old(
    auth_client, theme, django_capture_on_commit_callbacks
):
    video = create_video(theme, poster=make_image("old_poster.png"))
    old_path = video.poster.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            video_url(theme.id, video.id),
            {"poster": make_image("new_poster.png")},
            format="multipart",
        )

    assert response.status_code == 200
    video.refresh_from_db()
    assert video.poster.path != old_path
    assert os.path.exists(video.poster.path)
    assert not os.path.exists(old_path)


def test_patch_video_clears_poster_and_deletes_file(
    auth_client, theme, django_capture_on_commit_callbacks
):
    video = create_video(theme, poster=make_image("poster.png"))
    old_path = video.poster.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            video_url(theme.id, video.id), {"poster": ""}, format="multipart"
        )

    assert response.status_code == 200
    video.refresh_from_db()
    assert not video.poster
    assert not os.path.exists(old_path)


def test_patch_video_replaces_file_deletes_old_and_resets_duration(
    auth_client, theme, django_capture_on_commit_callbacks
):
    video = create_video(theme, name="old.mp4")
    video.duration = 30
    video.save()
    old_path = video.file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.patch(
            video_url(theme.id, video.id), {"file": make_video("new.mp4")}, format="multipart"
        )

    assert response.status_code == 200
    video.refresh_from_db()
    assert video.file.path != old_path
    assert os.path.exists(video.file.path)
    assert not os.path.exists(old_path)
    assert video.duration is None                    # the old duration no longer applies


def test_patch_video_with_bad_file_keeps_old_one(auth_client, theme):
    video = create_video(theme, name="keep.mp4")
    old_path = video.file.path

    response = auth_client.patch(
        video_url(theme.id, video.id), {"file": make_file("bad.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "file" in response.json()["errors"]
    assert os.path.exists(old_path)


def test_patch_video_with_bad_poster_rejected(auth_client, theme):
    video = create_video(theme)

    response = auth_client.patch(
        video_url(theme.id, video.id), {"poster": make_file("poster.txt")}, format="multipart"
    )

    assert response.status_code == 400
    assert "poster" in response.json()["errors"]


def test_patch_video_by_non_owner_forbidden(other_client, theme):
    video = create_video(theme, title="mine")

    response = other_client.patch(
        video_url(theme.id, video.id), {"title": "hijacked"}, format="multipart"
    )

    assert response.status_code == 403
    video.refresh_from_db()
    assert video.title == "mine"


def test_patch_video_of_another_theme_returns_404(auth_client, theme, other_theme):
    foreign = create_video(other_theme, title="theirs")

    response = auth_client.patch(
        video_url(theme.id, foreign.id), {"title": "taken"}, format="multipart"
    )

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.title == "theirs"


# DELETE /api/v1/themes/<id>/videos/<video_id>
def test_delete_video_removes_row_file_and_poster(
    auth_client, theme, django_capture_on_commit_callbacks
):
    video = create_video(theme, poster=make_image("poster.png"))
    paths = [video.file.path, video.poster.path]
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(video_url(theme.id, video.id))

    assert response.status_code == 200
    assert not Video.objects.filter(pk=video.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_video_without_poster(auth_client, theme, django_capture_on_commit_callbacks):
    video = create_video(theme)
    path = video.file.path

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(video_url(theme.id, video.id))

    assert response.status_code == 200
    assert not os.path.exists(path)


def test_delete_video_by_non_owner_forbidden(other_client, theme):
    video = create_video(theme)

    response = other_client.delete(video_url(theme.id, video.id))

    assert response.status_code == 403
    assert Video.objects.filter(pk=video.pk).exists()


def test_staff_can_delete_any_theme_video(staff_client, theme):
    video = create_video(theme)

    response = staff_client.delete(video_url(theme.id, video.id))

    assert response.status_code == 200
    assert not Video.objects.filter(pk=video.pk).exists()


def test_delete_video_of_another_theme_returns_404(auth_client, theme, other_theme):
    foreign = create_video(other_theme)

    response = auth_client.delete(video_url(theme.id, foreign.id))

    assert response.status_code == 404
    assert Video.objects.filter(pk=foreign.pk).exists()


def test_deleted_video_is_gone(auth_client, theme):
    video = create_video(theme)
    auth_client.delete(video_url(theme.id, video.id))

    assert auth_client.get(video_url(theme.id, video.id)).status_code == 404


def test_delete_video_requires_login(anon_client, theme):
    video = create_video(theme)

    assert anon_client.delete(video_url(theme.id, video.id)).status_code in (401, 403)
    assert Video.objects.filter(pk=video.pk).exists()


# =====================================================================
# DELETING A THEME REMOVES ITS MEDIA
# =====================================================================

def test_delete_theme_removes_its_images_and_videos(
    auth_client, theme, django_capture_on_commit_callbacks
):
    image = create_image(theme)
    video = create_video(theme, poster=make_image("poster.png"))
    paths = [image.file.path, video.file.path, video.poster.path]
    assert all(os.path.exists(path) for path in paths)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(f"/api/v1/themes/{theme.id}")

    assert response.status_code == 200
    assert not Theme.objects.filter(pk=theme.pk).exists()
    assert not Image.objects.filter(pk=image.pk).exists()
    assert not Video.objects.filter(pk=video.pk).exists()
    assert not any(os.path.exists(path) for path in paths)


def test_delete_theme_keeps_other_themes_media(
    auth_client, theme, other_theme, django_capture_on_commit_callbacks
):
    other_image = create_image(other_theme, name="theirs.png")
    other_video = create_video(other_theme, name="theirs.mp4")

    with django_capture_on_commit_callbacks(execute=True):
        auth_client.delete(f"/api/v1/themes/{theme.id}")

    assert Image.objects.filter(pk=other_image.pk).exists()
    assert Video.objects.filter(pk=other_video.pk).exists()
    assert os.path.exists(other_image.file.path)
    assert os.path.exists(other_video.file.path)