from datetime import datetime

from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.db.models import permalink

from mongoengine import *

class Tag(Document):
    tag = StringField(max_length=100, required=True)
    created = DateTimeField()
    
    @property
    def posts_for_tag(self):
        return BlogPost.published_posts().filter(tags=self)
    
    def save(self, **kwargs):
        if self.created is None:
            self.created = datetime.now()
        
        return super(Tag, self).save(**kwargs)
    
    @permalink
    def get_absolute_url(self):
        return ('tag_detail', [self.pk,])
    
    def __unicode__(self):
        return self.tag
    
    meta = {
        'ordering': ['-created'],
    }
    

class BlogPost(Document):
    published = BooleanField(default=False)
    author = StringField(required=True)
    title = StringField(required=True)
    slug = StringField()
    content = StringField(required=True)
    
    tags = ListField(ReferenceField(Tag))
    
    datetime_added = DateTimeField(default=datetime.now)
    
    def save(self):
        if self.slug is None:
            slug = slugify(self.title)
            new_slug = slug
            c = 1
            while True:
                try:
                    BlogPost.objects.get(slug=new_slug)
                except BlogPost.DoesNotExist:
                    break
                else:
                    c += 1
                    new_slug = '%s-%s' % (slug, c)
            self.slug = new_slug
        return super(BlogPost, self).save()
    
    def get_absolute_url(self):
        return '/%s/' % str(self.pk)
    
    @queryset_manager
    def published_posts(doc_cls, queryset):
        return queryset(published=True)

    meta = {
        'ordering': ['-datetime_added']
    }
