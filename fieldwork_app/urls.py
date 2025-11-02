from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    EmployeeViewSet,
    WorkRequestViewSet,
    WorkResultViewSet,
    WorkActViewSet,
    SyncLogViewSet
)

app_name = 'fieldwork'

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'work-requests', WorkRequestViewSet, basename='work-request')
router.register(r'work-results', WorkResultViewSet, basename='work-result')
router.register(r'work-acts', WorkActViewSet, basename='work-act')
router.register(r'sync-logs', SyncLogViewSet, basename='sync-log')

urlpatterns = [
    path('', include(router.urls)),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
