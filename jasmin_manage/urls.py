from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_nested import routers

from . import views

# Top-level router
router = routers.DefaultRouter()

# Routes for categories
router.register(r"categories", views.CategoryViewSet)

# Routes for collaborators
router.register(r"collaborators", views.CollaboratorViewSet)

# Routes for comments
router.register(r"comments", views.CommentViewSet)

# Routes for consortia
router.register(r"consortia", views.ConsortiumViewSet)
consortia_router = routers.NestedSimpleRouter(router, r"consortia", lookup="consortium")
# consortia_router.register(r'summary', views.ConsortiumViewSet, basename = 'consortium-summary')
consortia_router.register(
    r"projects", views.ConsortiumProjectsViewSet, basename="consortium-projects"
)
# consortia_router.register(r'summary', views.ConsortiumProjectsSummaryViewSet, basename = 'consortium-summary')

consortia_router.register(
    r"quotas", views.ConsortiumQuotasViewSet, basename="consortium-quotas"
)

# Routes for invitations
router.register(r"invitations", views.InvitationViewSet)

# Routes for projects
router.register(r"projects", views.ProjectViewSet)
projects_router = routers.NestedSimpleRouter(router, r"projects", lookup="project")
projects_router.register(
    r"collaborators",
    views.ProjectCollaboratorsViewSet,
    basename="project-collaborators",
)
projects_router.register(
    r"comments", views.ProjectCommentsViewSet, basename="project-comments"
)
projects_router.register(
    r"invitations", views.ProjectInvitationsViewSet, basename="project-invitations"
)
projects_router.register(
    r"services", views.ProjectServicesViewSet, basename="project-services"
)
projects_router.register(r"tags", views.ProjectTagsViewSet, basename="project-tags")

# Routes for requirements
router.register(r"requirements", views.RequirementViewSet)

# Routes for resources
router.register(r"resources", views.ResourceViewSet)

# Routes for services
router.register(r"services", views.ServiceViewSet)
services_router = routers.NestedSimpleRouter(router, r"services", lookup="service")
services_router.register(
    r"requirements", views.ServiceRequirementsViewSet, basename="service-requirements"
)
<<<<<<< HEAD

# Routes for tags
router.register(r"tags", views.TagViewSet)
=======
>>>>>>> short-proj-name

# Combine the URLs from all the routers to make the URL patterns
urlpatterns = [
    path("me/", views.CurrentUserView.as_view(), name="current-user"),
    path("join/", views.ProjectJoinView.as_view(), name="project-join"),
    path("", include(router.urls)),
    path("", include(consortia_router.urls)),
    path("", include(projects_router.urls)),
    path("", include(services_router.urls)),
    path("schema.json", SpectacularAPIView.as_view(), name="openapi-schema"),
    path(
        "doc/",
        SpectacularSwaggerView.as_view(url_name="openapi-schema"),
        name="openapi-docs",
    ),
]
