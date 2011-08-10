from django import forms
from mongoengine.base import ValidationError
from mongoengine.fields import EmbeddedDocumentField, ListField

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
            if hasattr(field.field, 'choices'):
                if not field.field.choices:
                    continue
            else:
                continue

        yield (field_name, field)
