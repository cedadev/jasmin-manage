from django.urls import include, path

from rest_framework_nested import routers

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views


# Top-level router
router = routers.DefaultRouter()

# Routes for categories
router.register(r'categories', views.CategoryViewSet)

# Routes for collaborators
router.register(r'collaborators', views.CollaboratorViewSet)

# Routes for consortia
router.register(r'consortia', views.ConsortiumViewSet)
consortia_router = routers.NestedSimpleRouter(router, r'consortia', lookup = 'consortium')
consortia_router.register(r'projects', views.ConsortiumProjectsViewSet, basename = 'consortium-projects')
consortia_router.register(r'quotas', views.ConsortiumQuotasViewSet, basename = 'consortium-quotas')

# Routes for projects
router.register(r'projects', views.ProjectViewSet)
projects_router = routers.NestedSimpleRouter(router, r'projects', lookup = 'project')
projects_router.register(r'collaborators', views.ProjectCollaboratorsViewSet, basename = 'project-collaborators')
projects_router.register(r'services', views.ProjectServicesViewSet, basename = 'project-services')

# Routes for requirements
router.register(r'requirements', views.RequirementViewSet)

# Routes for resources
router.register(r'resources', views.ResourceViewSet)

# Routes for services
router.register(r'services', views.ServiceViewSet)
services_router = routers.NestedSimpleRouter(router, r'services', lookup = 'service')
services_router.register(r'requirements', views.ServiceRequirementsViewSet, basename = 'service-requirements')


# Combine the URLs from all the routers to make the URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('', include(consortia_router.urls)),
    path('', include(projects_router.urls)),
    path('', include(services_router.urls)),
    path('schema.json', SpectacularAPIView.as_view(), name = 'openapi-schema'),
    path('doc/', SpectacularSwaggerView.as_view(url_name = 'openapi-schema'), name = 'openapi-docs'),
]
