from __future__ import unicode_literals

from django.urls import re_path
from plumbing.views import api_node

urlpatterns = [
    re_path(r'^$', api_node, name='api_node'),
    re_path(r'^(?P<node_type>\w+)/$', api_node, name='api_node'),
    re_path(r'^(?P<node_type>\w+)/(?P<node_id>\d+)$', api_node, name='api_node'),
]
