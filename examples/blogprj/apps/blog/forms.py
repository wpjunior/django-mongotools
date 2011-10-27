# -*- coding: utf-8 -*-

from django import forms
from mongotools.forms import MongoForm
from models import BlogPost, Tag

class TagForm(MongoForm):
    class Meta:
        document = Tag
        fields = ('tag',)

class BlogPostForm(MongoForm):
    class Meta:
        document = BlogPost
        fields = ('author', 'title', 'content', 'published', 'tags',)
    content = forms.CharField(widget=forms.Textarea)
