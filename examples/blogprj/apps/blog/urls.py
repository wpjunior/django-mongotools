# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to, direct_to_template
from views import (AddPostView, UpdatePostView, PostIndexView,
                   PostDetailView, DeletePostView, AddTagView, 
                   UpdateTagView, TagDetailView)

entry_pattern = patterns('',
    (r'^$', PostDetailView.as_view()),
    (r'^edit/$', UpdatePostView.as_view()),
    (r'^delete/$', DeletePostView.as_view() ),
)

tag_pattern = patterns('',
    url(r'^$', TagDetailView.as_view(), name='tag_detail'),
    (r'^edit/$', UpdateTagView.as_view()),
)

urlpatterns = patterns('apps.blog.views',
    (r'^$', PostIndexView.as_view()),
    (r'^new/$', AddPostView.as_view()),
    (r'^newtag/$', AddTagView.as_view()),
    (r'^(?P<pk>\w{24})/', include(entry_pattern)),
    (r'^tags/(?P<pk>\w+)/', include(tag_pattern)),
)
