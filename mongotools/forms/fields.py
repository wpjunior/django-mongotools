from django import forms
from django.utils.encoding import smart_unicode
from pymongo.errors import InvalidId
from pymongo.objectid import ObjectId
from django.core.validators import EMPTY_VALUES
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.translation import ugettext_lazy as _

from mongoengine import ReferenceField as MongoReferenceField

BLANK_CHOICE_DASH = [("", "---------")]

class MongoChoiceIterator(object):
    def __init__(self, field):
        self.field = field
        self.queryset = field.queryset

    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)
        
        for obj in self.queryset.all():
            yield self.choice(obj)

    def __len__(self):
        return len(self.queryset)

    def choice(self, obj):
        return (self.field.prepare_value(obj), self.field.label_from_instance(obj))


class MongoCharField(forms.CharField):
    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        return smart_unicode(value)

class ReferenceField(forms.ChoiceField):
    """
    Reference field for mongo forms. Inspired by `django.forms.models.ModelChoiceField`.
    """
    def __init__(self, queryset, empty_label=u"---------",
                 *aargs, **kwaargs):
        
        forms.Field.__init__(self, *aargs, **kwaargs)
        self.queryset = queryset
        self.empty_label = empty_label
        
    def _get_queryset(self):
        return self._queryset
        
    def prepare_value(self, value):
        if hasattr(value, '_meta'):
            return value.pk
        
        return super(ReferenceField, self).prepare_value(value)

    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    def _get_choices(self):
        return MongoChoiceIterator(self)

    choices = property(_get_choices, forms.ChoiceField._set_choices)
    
    def label_from_instance(self, obj):
        """
        This method is used to convert objects into strings; it's used to
        generate the labels for the choices presented by this object. Subclasses
        can override this method to customize the display of the choices.
        """
        return smart_unicode(obj)

    def clean(self, value):
        if value in EMPTY_VALUES and not self.required:
            return None

        try:
            oid = ObjectId(value)
            oid = super(ReferenceField, self).clean(oid)

            queryset = self.queryset.clone()
            obj = queryset.get(id=oid)
        except (TypeError, InvalidId, self.queryset._document.DoesNotExist):
            raise forms.ValidationError(self.error_messages['invalid_choice'] % {'value':value})
        return obj

class DocumentMultipleChoiceField(ReferenceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""
    widget = forms.SelectMultiple   
    hidden_widget = forms.MultipleHiddenInput
    default_error_messages = {
        'list': _(u'Enter a list of values.'),
        'invalid_choice': _(u'Select a valid choice. %s is not one of the'
                            u' available choices.'),
        'invalid_pk_value': _(u'"%s" is not a valid value for a primary key.')
    }

    def __init__(self, queryset, *args, **kwargs):
        super(DocumentMultipleChoiceField, self).__init__(queryset, empty_label=None, *args, **kwargs)  

    def clean(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise forms.ValidationError(self.error_messages['list'])
        key = 'pk'
        
        filter_ids = []
        for pk in value:
            try:
                oid = ObjectId(pk)
                filter_ids.append(oid)
            except InvalidId:
                raise forms.ValidationError(self.error_messages['invalid_pk_value'] % pk)
        qs = self.queryset.clone()
        qs = qs.filter(**{'%s__in' % key: filter_ids})
        pks = set([force_unicode(getattr(o, key)) for o in qs])
        for val in value:
            if force_unicode(val) not in pks:
                raise forms.ValidationError(self.error_messages['invalid_choice'] % val)
        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(value)
        return list(qs)

    def prepare_value(self, value):
        if hasattr(value, '__iter__') and not hasattr(value, '_meta'):
            return [super(DocumentMultipleChoiceField, self).prepare_value(v) for v in value]
        return super(DocumentMultipleChoiceField, self).prepare_value(value)


class MongoFormFieldGenerator(object):
    """This is singleton class generates Django form-fields for mongoengine-fields."""
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MongoFormFieldGenerator, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def generate(self, field, **kwargs):
        """Tries to lookup a matching formfield generator (lowercase 
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """
        if hasattr(self, 'generate_%s' % field.__class__.__name__.lower()):
            return getattr(self, 'generate_%s' % \
                field.__class__.__name__.lower())(field, **kwargs)
        else:
            for cls in field.__class__.__bases__:
                if hasattr(self, 'generate_%s' % cls.__name__.lower()):
                    return getattr(self, 'generate_%s' % \
                                       cls.__name__.lower())(field, **kwargs)

            raise NotImplementedError('%s is not supported by MongoForm' % \
                                          field.__class__.__name__)
                
    def get_field_choices(self, field, include_blank=True,
                          blank_choice=BLANK_CHOICE_DASH):
        first_choice = include_blank and blank_choice or []
        return first_choice + list(field.choices)

    def string_field(self, value):
        if value in EMPTY_VALUES:
            return None
        return smart_unicode(value)

    def integer_field(self, value):
        if value in EMPTY_VALUES:
            return None
        return int(value)

    def boolean_field(self, value):
        if value in EMPTY_VALUES:
            return None
        return value.lower() == 'true'

    def get_field_label(self, field):
        if field.verbose_name:
            return field.verbose_name
        return field.name.capitalize()

    def get_field_help_text(self, field):
        if field.help_text:
            return field.help_text.capitalize()

    def generate_stringfield(self, field, **kwargs):
        form_class = MongoCharField

        defaults = {'label': self.get_field_label(field),
                    'initial': field.default,
                    'required': field.required,
                    'help_text': self.get_field_help_text(field)}

        # use to get a custom widget
        if hasattr(field, 'get_custom_widget'):
            defaults['widget'] = field.get_custom_widget()

        if field.max_length and not field.choices:
            defaults['max_length'] = field.max_length
            
        if field.max_length is None and not field.choices:
            defaults['widget'] = forms.Textarea

        if field.regex:
            defaults['regex'] = field.regex
        elif field.choices:
            form_class = forms.TypedChoiceField
            defaults['choices'] = self.get_field_choices(field)
            defaults['coerce'] = self.string_field

            if not field.required:
                defaults['empty_value'] = None
                
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_emailfield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'initial': field.default,
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field)    
        }
        
        defaults.update(kwargs)
        return forms.EmailField(**defaults)

    def generate_urlfield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'initial': field.default,
            'label': self.get_field_label(field),
            'help_text':  self.get_field_help_text(field)
        }
        
        defaults.update(kwargs)
        return forms.URLField(**defaults)

    def generate_intfield(self, field, **kwargs):
        if field.choices:
            defaults = {
                'coerce': self.integer_field,
                'empty_value': None,
                'required': field.required,
                'initial': field.default,
                'label': self.get_field_label(field),
                'choices': self.get_field_choices(field),
                'help_text': self.get_field_help_text(field)        
            }
            
            defaults.update(kwargs)
            return forms.TypedChoiceField(**defaults)
        else:
            defaults = {
                'required': field.required,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'initial': field.default,
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field)      
            }
            
            defaults.update(kwargs)
            return forms.IntegerField(**defaults)

    def generate_floatfield(self, field, **kwargs):

        form_class = forms.FloatField

        defaults = {'label': self.get_field_label(field),
                    'initial': field.default,
                    'required': field.required,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'help_text': self.get_field_help_text(field)}

        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_decimalfield(self, field, **kwargs):
        form_class = forms.DecimalField
        defaults = {'label': self.get_field_label(field),
                    'initial': field.default,
                    'required': field.required,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'help_text': self.get_field_help_text(field)}

        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_booleanfield(self, field, **kwargs):
        if field.choices:
            defaults = {
                'coerce': self.boolean_field,
                'empty_value': None,
                'required': field.required,
                'initial': field.default,
                'label': self.get_field_label(field),
                'choices': self.get_field_choices(field),
                'help_text': self.get_field_help_text(field)        
            }
            
            defaults.update(kwargs)
            return forms.TypedChoiceField(**defaults)
        else:
            defaults = {
                'required': field.required,
                'initial': field.default,
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field)     
                }
            
            defaults.update(kwargs)
            return forms.BooleanField(**defaults)

    def generate_datetimefield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'initial': field.default,
            'label': self.get_field_label(field),
        }
        
        defaults.update(kwargs)
        return forms.DateTimeField(**defaults)

    def generate_referencefield(self, field, **kwargs):
        defaults = {
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field),
            'required': field.required
        }
        
        defaults.update(kwargs)
        return ReferenceField(field.document_type.objects, **defaults)

    def generate_listfield(self, field, **kwargs):
        if field.field.choices:
            defaults = {
                'choices': field.field.choices,
                'required': field.required,
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field),
                'widget': forms.CheckboxSelectMultiple     
            }
            
            defaults.update(kwargs)
            return forms.MultipleChoiceField(**defaults)
        elif isinstance(field.field, MongoReferenceField):
            defaults = {
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field),
                'required': field.required
            }
        
            defaults.update(kwargs)
            f = DocumentMultipleChoiceField(field.field.document_type.objects, **defaults)
            return f
        
    def generate_filefield(self, field, **kwargs):
        return forms.FileField(**kwargs)
