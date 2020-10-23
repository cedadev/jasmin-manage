from django.urls import include, path

from rest_framework import routers

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views


# Top-level router
router = routers.DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'consortia', views.ConsortiumViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'quotas', views.QuotaViewSet)
router.register(r'requirements', views.RequirementViewSet)
router.register(r'resources', views.ResourceViewSet)
router.register(r'services', views.ServiceViewSet)


# Combine the URLs from all the routers to make the URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('schema/', SpectacularAPIView.as_view(), name = 'openapi-schema'),
    path('doc/', SpectacularSwaggerView.as_view(url_name = 'openapi-schema'), name = 'openapi-docs'),
]
