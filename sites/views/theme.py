from rest_framework import status
from rest_framework.views import APIView
from sites.responses import success_response
from sites.pagination import DefaultPagination
from rest_framework.permissions import IsAuthenticated
from sites.services.theme import ThemeService, ThemeImageService
from sites.serializers.theme import ThemeCreateInputSerializer, ThemeOuputSerializer 
from sites.serializers.theme import ThemeListQuerySerializer, ThemeImageCreateInputSerializer, ImageOutputSerializer


class ThemeList(APIView):
    """
    GET  /themes/  -> list themes
    POST /themes/  -> create a theme
    """

    permission_classes = [IsAuthenticated]

    # DI
    services = ThemeService
    create_input_serializer = ThemeCreateInputSerializer
    output_serializer = ThemeOuputSerializer
    list_query_serializer = ThemeListQuerySerializer
    pagination_class = DefaultPagination

    def get(self, request):
        query = self.list_query_serializer(data=request.query_params, partial=True)
        query.is_valid(raise_exception=True)

        themes = self.services.list(**query.validated_data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(themes, request, view=self)
        items = self.output_serializer(page, many=True).data

        return success_response(paginator.get_paginated_data(items), "Themes retrieved")
 
    def post(self, request):
        serializer = self.create_input_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        theme = self.services.create(**serializer.validated_data)

        return success_response(
            self.output_serializer(theme).data,
            "Theme created",
            status.HTTP_201_CREATED,
        )

class ThemeDetail(APIView):
    """
    GET    /themes/{theme_id}/  -> theme detail
    PATCH  /themes/{theme_id}/  -> update theme
    DELETE /themes/{theme_id}/  -> delete theme
    """

    permission_classes = [IsAuthenticated]

    services = ThemeService
    output_serializer = ThemeOuputSerializer
    
    def get(self, request, theme_id):
        theme = self.services.get(theme_id=theme_id)

        return success_response(
            self.output_serializer(theme).data,
            "Theme retrieved",
        )
 
    def patch(self, request, theme_id):
        pass
 
    def delete(self, request, theme_id):
        self.services.delete(theme_id=theme_id, user=request.user)
        return success_response(message="Theme deleted")
 
 
class ThemeImageList(APIView):
    """
    GET  /themes/{theme_id}/images/  -> list theme images
    POST /themes/{theme_id}/images/  -> upload a theme image
    """

    permission_classes = [IsAuthenticated]

    services = ThemeImageService
    create_input_serializer = ThemeImageCreateInputSerializer
    output_serializer = ImageOutputSerializer
    
    def get(self, request, theme_id):
        images = self.services.list(theme_id=theme_id)

        return success_response(
            self.output_serializer(images, many=True).data,
            "Images retrieved",
        )
 
    def post(self, request, theme_id):
        serializer = self.create_input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        images = self.services.create(
            theme_id=theme_id, user=request.user, **serializer.validated_data
        )

        return success_response(
            self.output_serializer(images, many=True).data,
            "Images uploaded",
            status.HTTP_201_CREATED,
        )
 
 
class ThemeImageDetail(APIView):
    """
    GET    /themes/{theme_id}/images/{image_id}/  -> image detail
    PATCH  /themes/{theme_id}/images/{image_id}/  -> update image (alt text, file)
    DELETE /themes/{theme_id}/images/{image_id}/  -> delete image
    """
 
    def get(self, request, theme_id, image_id):
        pass
 
    def patch(self, request, theme_id, image_id):
        pass
 
    def delete(self, request, theme_id, image_id):
        pass
 
 
class ThemeVideoList(APIView):
    """
    GET  /themes/{theme_id}/videos/  -> list theme videos
    POST /themes/{theme_id}/videos/  -> upload a theme video
    """
 
    def get(self, request, theme_id):
        pass
 
    def post(self, request, theme_id):
        pass
 
 
class ThemeVideoDetail(APIView):
    """
    GET    /themes/{theme_id}/videos/{video_id}/  -> video detail
    PATCH  /themes/{theme_id}/videos/{video_id}/  -> update video (title, poster, file)
    DELETE /themes/{theme_id}/videos/{video_id}/  -> delete video
    """
 
    def get(self, request, theme_id, video_id):
        pass
 
    def patch(self, request, theme_id, video_id):
        pass
 
    def delete(self, request, theme_id, video_id):
        pass
 