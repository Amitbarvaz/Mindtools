from __future__ import unicode_literals

from django.urls import include, re_path
from rest_framework import routers

from system.views import VariableViewSet, VariableSearchViewSet, ExpressionViewSet


router = routers.DefaultRouter()
router.register(r'variables/search', VariableSearchViewSet)
router.register(r'evaluate-expression', ExpressionViewSet, basename="evaluate-expression-viewset")
router.register(r'variables', VariableViewSet, basename="variable-viewset")

urlpatterns = [
    re_path(r'', include(router.urls)),
]

