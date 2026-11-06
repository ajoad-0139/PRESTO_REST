
from rest_framework.views import APIView

class PageList(APIView):
    """
    GET  /sites/{site_id}/pages/  -> list pages of a site
    POST /sites/{site_id}/pages/  -> create a page
    """
 
    def get(self, request, site_id):
        pass
 
    def post(self, request, site_id):
        pass
 
 
class PageDetail(APIView):
    """
    GET    /sites/{site_id}/pages/{page_id}/  -> page detail
    PATCH  /sites/{site_id}/pages/{page_id}/  -> update page
    DELETE /sites/{site_id}/pages/{page_id}/  -> delete page
    """
 
    def get(self, request, site_id, page_id):
        pass
 
    def patch(self, request, site_id, page_id):
        pass
 
    def delete(self, request, site_id, page_id):
        pass
 