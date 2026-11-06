from rest_framework.views import APIView

class SiteList(APIView):
    """
    GET  /sites/  -> list the current user's sites
    POST /sites/  -> create a site
    """
 
    def get(self, request):
        pass
 
    def post(self, request):
        pass
 

 
class SiteDetail(APIView):
    """
    GET    /sites/{site_id}/  -> site detail
    PATCH  /sites/{site_id}/  -> update site
    DELETE /sites/{site_id}/  -> delete site
    """
 
    def get(self, request, site_id):
        pass
 
    def patch(self, request, site_id):
        pass
 
    def delete(self, request, site_id):
        pass


class SiteImageList(APIView):
    """
    GET  /sites/{site_id}/images/  -> list site images (?page=<uuid> to filter)
    POST /sites/{site_id}/images/  -> upload a site image
    """

    def get(self, request, site_id):
        pass

    def post(self, request, site_id):
        pass

 
class SiteImageDetail(APIView):
    """
    GET    /sites/{site_id}/images/{image_id}/  -> image detail
    PATCH  /sites/{site_id}/images/{image_id}/  -> update image (alt text, file)
    DELETE /sites/{site_id}/images/{image_id}/  -> delete image
    """
 
    def get(self, request, site_id, image_id):
        pass
 
    def patch(self, request, site_id, image_id):
        pass
 
    def delete(self, request, site_id, image_id):
        pass
 
 
class SiteVideoList(APIView):
    """
    GET  /sites/{site_id}/videos/  -> list site videos (?page=<uuid> to filter)
    POST /sites/{site_id}/videos/  -> upload a site video
    """
 
    def get(self, request, site_id):
        pass
 
    def post(self, request, site_id):
        pass
 
 
class SiteVideoDetail(APIView):
    """
    GET    /sites/{site_id}/videos/{video_id}/  -> video detail
    PATCH  /sites/{site_id}/videos/{video_id}/  -> update video (title, poster, file)
    DELETE /sites/{site_id}/videos/{video_id}/  -> delete video
    """
 
    def get(self, request, site_id, video_id):
        pass
 
    def patch(self, request, site_id, video_id):
        pass
 
    def delete(self, request, site_id, video_id):
        pass