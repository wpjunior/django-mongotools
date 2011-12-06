import os
import itertools
import gridfs

from django import forms
from mongoengine.base import ValidationError
from mongoengine.fields import EmbeddedDocumentField, ListField, ReferenceField
from mongoengine.connection import _get_db

from fields import MongoFormFieldGenerator

def generate_field(field):
    generator = MongoFormFieldGenerator()
    return generator.generate(field)

def mongoengine_validate_wrapper(field, old_clean, new_clean):
    """
    A wrapper function to validate formdata against mongoengine-field
    validator and raise a proper django.forms ValidationError if there
    are any problems.
    """
    def inner_validate(value):
        value = old_clean(value)

        if value is None and field.required:
            raise ValidationError("This field is required")

        elif value is None:
            return value
        try:
            new_clean(value)
            return value
        except ValidationError, e:
            raise forms.ValidationError(e)
    return inner_validate

def iter_valid_fields(meta):
    """walk through the available valid fields.."""

    # fetch field configuration and always add the id_field as exclude
    meta_fields = getattr(meta, 'fields', ())
    meta_exclude = getattr(meta, 'exclude', ()) + (meta.document._meta.get('id_field'),)
    # walk through the document fields

    for field_name, field in sorted(meta.document._fields.items(), key=lambda t: t[1].creation_counter):
        # skip excluded or not explicit included fields
        if (meta_fields and field_name not in meta_fields) or field_name in meta_exclude:
            continue

        if isinstance(field, EmbeddedDocumentField): #skip EmbeddedDocumentField
            continue

        if isinstance(field, ListField):
            if hasattr(field.field, 'choices') and not isinstance(field.field, ReferenceField):
                if not field.field.choices:
                    continue
            if not isinstance(field.field, ReferenceField):
                continue

        yield (field_name, field)

def _get_unique_filename(name):
    fs = gridfs.GridFS(_get_db())
    file_root, file_ext = os.path.splitext(name)
    count = itertools.count(1)
    while fs.exists(filename=name):
        # file_ext includes the dot.
        name = os.path.join("%s_%s%s" % (file_root, count.next(), file_ext))
    return name

def save_file(instance, field_name, file):
    field = getattr(instance, field_name)
    filename = _get_unique_filename(file.name)
    # seek to start to make sure we get the whole file
    file.file.seek(0)
    field.replace(file, content_type=file.content_type, filename=filename)
    return field
