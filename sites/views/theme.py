from rest_framework import status
from rest_framework.views import APIView
from sites.services.theme import ThemeService
from sites.responses import success_response
from rest_framework.permissions import IsAuthenticated
from sites.serializers.theme import ThemeCreateInputSerializer, ThemeOuputSerializer


class ThemeList(APIView):
    """
    GET  /themes/  -> list themes
    POST /themes/  -> create a theme
    """

    permission_classes = [IsAuthenticated]

    services = ThemeService
    create_input_serializer = ThemeCreateInputSerializer
    output_serializer = ThemeOuputSerializer

    def get(self, request):
        pass
 
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
 
    def get(self, request, theme_id):
        pass
 
    def patch(self, request, theme_id):
        pass
 
    def delete(self, request, theme_id):
        pass
 
 
class ThemeImageList(APIView):
    """
    GET  /themes/{theme_id}/images/  -> list theme images
    POST /themes/{theme_id}/images/  -> upload a theme image
    """
 
    def get(self, request, theme_id):
        pass
 
    def post(self, request, theme_id):
        pass
 
 
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
 