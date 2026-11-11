from django.urls import path

from sites.views.page import PageList, PageDetail
from sites.views.auth import CsrfView, LoginView, LogoutView, MeView
from sites.views.theme import ThemeList, ThemeDetail, ThemeImageList, ThemeImageDetail, ThemeVideoList, ThemeVideoDetail
from sites.views.site import SiteList, SiteDetail, SiteImageList, SiteImageDetail, SiteVideoList, SiteVideoDetail

urlpatterns = [

    path("auth/csrf", CsrfView.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/me", MeView.as_view()),

    # theme api paths
    path("themes", ThemeList.as_view(), name="theme-list"),                                  
    path("themes/<uuid:theme_id>", ThemeDetail.as_view(), name="theme-detail"),             
    path("themes/<uuid:theme_id>/images", ThemeImageList.as_view(), name="theme-image-list"), 
    path("themes/<uuid:theme_id>/images/<uuid:image_id>", ThemeImageDetail.as_view(), name="theme-image-detail"), # pending
    path("themes/<uuid:theme_id>/videos", ThemeVideoList.as_view(), name="theme-video-list"), 
    path("themes/<uuid:theme_id>/videos/<uuid:video_id>", ThemeVideoDetail.as_view(), name="theme-video-detail"), # pending

    # site api paths
    path("sites", SiteList.as_view(), name="site-list"),                                     
    path("sites/<uuid:site_id>", SiteDetail.as_view(), name="site-detail"),   
    path("sites/<uuid:site_id>/images", SiteImageList.as_view(), name="site-image-list"),             
    path("sites/<uuid:site_id>/images/<uuid:image_id>", SiteImageDetail.as_view(), name="site-image-detail"), 
    path("sites/<uuid:site_id>/videos", SiteVideoList.as_view(), name="site-video-list"),  
    path("sites/<uuid:site_id>/videos/<uuid:video_id>", SiteVideoDetail.as_view(), name="site-video-detail"),   

    # page api paths
    path("sites/<uuid:site_id>/pages", PageList.as_view(), name="page-list"),                        
    path("sites/<uuid:site_id>/pages/<uuid:page_id>", PageDetail.as_view(), name="page-detail"),     

]