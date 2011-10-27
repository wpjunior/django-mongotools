# -*- coding: utf-8 -*-

from mongotools.views import (CreateView, UpdateView,
                              DeleteView, ListView,
                              DetailView)

from models import BlogPost, Tag
from forms import BlogPostForm, TagForm

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

class TagDetailView(DetailView):
    document = Tag

class AddTagView(CreateView):
    document = Tag
    success_url = '/'
    form_class = TagForm

class UpdateTagView(UpdateView):
    document = Tag
    form_class = TagForm
