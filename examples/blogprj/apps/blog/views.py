# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from mongotools.views import (CreateView, UpdateView,
                              DeleteView, ListView,
                              DetailView)

from models import BlogPost
from forms import BlogPostForm

class PostIndexView(ListView):
    document = BlogPost

class PostDetailView(DetailView):
    document = BlogPost

class AddPostView(CreateView):
    document = BlogPost
    success_url = '/'
    form_class = BlogPostForm

class DeletePostView(DeleteView):
    document = BlogPost
    success_url = '/'

class UpdatePostView(UpdateView):
    document = BlogPost
    form_class = BlogPostForm
