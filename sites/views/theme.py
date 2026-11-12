from rest_framework import status
from rest_framework.views import APIView
from sites.responses import success_response
from sites.pagination import DefaultPagination
from rest_framework.permissions import IsAuthenticated
from sites.services.theme import (ThemeService, ThemeImageService , ThemeVideoService)
from sites.serializers.asset import ImageOutputSerializer, VideoOutputSerializer
from sites.serializers.theme import (ThemeCreateInputSerializer, ThemeOuputSerializer , ThemeVideoCreateInputSerializer,
    ThemeListQuerySerializer, ThemeImageCreateInputSerializer, ThemeImageUpdateInputSerializer, ThemeImageOutputSerializer,
    ThemeVideoOutputSerializer, ThemeVideoUpdateInputSerializer)


class ThemeList(APIView):
    """Handle listing and creating themes."""

    permission_classes = [IsAuthenticated]

    # DI
    services = ThemeService
    create_input_serializer = ThemeCreateInputSerializer
    output_serializer = ThemeOuputSerializer
    list_query_serializer = ThemeListQuerySerializer
    pagination_class = DefaultPagination

    def get(self, request):
        """Retrieve themes with optional filtering and pagination.

        Args:
            request: HTTP request containing query parameters.

        Returns:
            Response containing paginated themes.
        """


        query = self.list_query_serializer(data=request.query_params, partial=True)
        query.is_valid(raise_exception=True)

        themes = self.services.list(**query.validated_data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(themes, request, view=self)
        items = self.output_serializer(page, many=True).data

        return success_response(paginator.get_paginated_data(items), "Themes retrieved")
 
    def post(self, request):
        """Create a new theme.

        Args:
            request: HTTP request containing theme data.

        Returns:
            Response containing the created theme.
        """


        serializer = self.create_input_serializer(data=request.data , context={"request": request},)
        serializer.is_valid(raise_exception=True)

        theme = self.services.create(**serializer.validated_data)

        return success_response(
            self.output_serializer(theme).data,
            "Theme created",
            status.HTTP_201_CREATED,
        )

class ThemeDetail(APIView):
    """Handle retrieving, updating, and deleting a theme."""

    permission_classes = [IsAuthenticated]

    services = ThemeService
    output_serializer = ThemeOuputSerializer
    update_input_serializer = ThemeCreateInputSerializer 
    
    def get(self, request, theme_id):
        """Retrieve a theme by its ID.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.

        Returns:
            Response containing the theme.
        """


        theme = self.services.get(theme_id=theme_id)

        return success_response(
            self.output_serializer(theme).data,
            "Theme retrieved",
        )
 
    def patch(self, request, theme_id):
        """Partially update a theme.

        Args:
            request: HTTP request containing fields to update.
            theme_id: ID of the theme.

        Returns:
            Response containing the updated theme.
        """


        serializer = self.update_input_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        theme = self.services.update(theme_id=theme_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(theme).data,
            "Theme updated",
        )
 
    def delete(self, request, theme_id):
        """Delete a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.

        Returns:
            Response confirming deletion.
        """


        self.services.delete(theme_id=theme_id, user=request.user)
        return success_response(message="Theme deleted")
 
 
class ThemeImageList(APIView):
    """Handle listing and uploading images for a theme."""

    permission_classes = [IsAuthenticated]

    services = ThemeImageService
    create_input_serializer = ThemeImageCreateInputSerializer
    output_serializer = ImageOutputSerializer
    
    def get(self, request, theme_id):
        """Retrieve images belonging to a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.

        Returns:
            Response containing serialized images.
        """


        images = self.services.list(theme_id=theme_id)

        return success_response(
            self.output_serializer(images, many=True).data,
            "Images retrieved",
        )
 
    def post(self, request, theme_id):
        """Upload images to a theme.

        Args:
            request: HTTP request containing image files and metadata.
            theme_id: ID of the theme.

        Returns:
            Response containing the uploaded images.
        """


        serializer = self.create_input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        images = self.services.create(theme_id=theme_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(images, many=True).data,
            "Images uploaded",
            status.HTTP_201_CREATED,
        )
 
 
class ThemeImageDetail(APIView):
    """Handle retrieving, updating, and deleting a theme image."""

    permission_classes = [IsAuthenticated]

    services = ThemeImageService
    update_input_serializer = ThemeImageUpdateInputSerializer
    output_serializer = ThemeImageOutputSerializer
 
    def get(self, request, theme_id, image_id):
        """Retrieve an image belonging to a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.
            image_id: ID of the image.

        Returns:
            Response containing the image.
        """


        image = self.services.get(theme_id=theme_id, image_id=image_id)

        return success_response(
            self.output_serializer(image).data,
            "Image retrieved",
        )
 
    def patch(self, request, theme_id, image_id):
        """Partially update a theme image.

        Args:
            request: HTTP request containing image fields to update.
            theme_id: ID of the theme.
            image_id: ID of the image.

        Returns:
            Response containing the updated image.
        """


        serializer = self.update_input_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        image = self.services.update(theme_id=theme_id, image_id=image_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(image).data,
            "Image updated",
        )
 
    def delete(self, request, theme_id, image_id):
        """Delete an image from a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.
            image_id: ID of the image.

        Returns:
            Response confirming deletion.
        """


        self.services.delete(theme_id=theme_id, image_id=image_id, user=request.user)

        return success_response(message="Image deleted")
 
 
class ThemeVideoList(APIView):
    """Handle listing and uploading videos for a theme."""

    permission_classes = [IsAuthenticated]

    services = ThemeVideoService
    create_input_serializer = ThemeVideoCreateInputSerializer
    output_serializer = VideoOutputSerializer
 
    def get(self, request, theme_id):
        """Retrieve videos belonging to a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.

        Returns:
            Response containing serialized videos.
        """


        videos = self.services.list(theme_id=theme_id)

        return success_response(
            self.output_serializer(videos, many=True).data,
            "Videos retrieved",
        )
 
    def post(self, request, theme_id):
        """Upload videos to a theme.

        Args:
            request: HTTP request containing video files and metadata.

        Returns:
            Response containing the uploaded videos.
        """

         
        serializer = self.create_input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        videos = self.services.create(theme_id=theme_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(videos, many=True).data,
            "Videos uploaded",
            status.HTTP_201_CREATED,
        )
 
 
class ThemeVideoDetail(APIView):
    """Handle retrieving, updating, and deleting a theme video."""

    permission_classes = [IsAuthenticated]

    services = ThemeVideoService
    update_input_serializer = ThemeVideoUpdateInputSerializer
    output_serializer = ThemeVideoOutputSerializer
 
    def get(self, request, theme_id, video_id):
        """Retrieve a video belonging to a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.
            video_id: ID of the video.

        Returns:
            Response containing the video.
        """


        video = self.services.get(theme_id=theme_id, video_id=video_id)

        return success_response(
            self.output_serializer(video).data,
            "Video retrieved",
        )
 
    def patch(self, request, theme_id, video_id):
        """Partially update a theme video.

        Args:
            request: HTTP request containing video fields to update.
            theme_id: ID of the theme.
            video_id: ID of the video.

        Returns:
            Response containing the updated video.
        """


        serializer = self.update_input_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        video = self.services.update(theme_id=theme_id, video_id=video_id, user=request.user, **serializer.validated_data,)

        return success_response(
            self.output_serializer(video).data,
            "Video updated",
        )
 
    def delete(self, request, theme_id, video_id):
        """Delete a video from a theme.

        Args:
            request: HTTP request.
            theme_id: ID of the theme.
            video_id: ID of the video.

        Returns:
            Response confirming deletion.
        """

        
        self.services.delete(theme_id=theme_id,video_id=video_id,user=request.user)

        return success_response(message="Video deleted")
 