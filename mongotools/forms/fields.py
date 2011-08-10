from django import forms
from django.utils.encoding import smart_unicode
from pymongo.errors import InvalidId
from pymongo.objectid import ObjectId
from django.core.validators import EMPTY_VALUES
from django.utils.encoding import smart_unicode

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

class MongoFormFieldGenerator(object):
    """This class generates Django form-fields for mongoengine-fields."""
    
    def generate(self, field_name, field):
        """Tries to lookup a matching formfield generator (lowercase 
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """
        if hasattr(self, 'generate_%s' % field.__class__.__name__.lower()):
            return getattr(self, 'generate_%s' % \
                field.__class__.__name__.lower())(field_name, field)
        else:
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

    def get_field_label(self, field_name, field):
        if field.verbose_name:
            return field.verbose_name.capitalize()
        return field_name.capitalize()

    def get_field_help_text(self, field):
        if field.help_text:
            return field.help_text.capitalize()

    def generate_stringfield(self, field_name, field):
        form_class = MongoCharField

        defaults = {'label': self.get_field_label(field_name, field),
                    'initial': field.default,
                    'required': field.required,
                    'help_text': self.get_field_help_text(field)}

        if field.max_length and not field.choices:
            defaults['max_length'] = field.max_length

        if field.regex:
            defaults['regex'] = field.regex
        elif field.choices:
            form_class = forms.TypedChoiceField
            defaults['choices'] = self.get_field_choices(field)
            defaults['coerce'] = self.string_field

            if not field.required:
                defaults['empty_value'] = None

        return form_class(**defaults)

    def generate_emailfield(self, field_name, field):
        return forms.EmailField(
            required=field.required,
            min_length=field.min_length,
            max_length=field.max_length,
            initial=field.default,
            label=self.get_field_label(field_name, field),
            help_text= self.get_field_help_text(field)
        )

    def generate_urlfield(self, field_name, field):
        return forms.URLField(
            required=field.required,
            min_length=field.min_length,
            max_length=field.max_length,
            initial=field.default,
            label=self.get_field_label(field_name, field),
            help_text= self.get_field_help_text(field)
        )

    def generate_intfield(self, field_name, field):
        if field.choices:
            return forms.TypedChoiceField(
                coerce=self.integer_field,
                empty_value=None,
                required=field.required,
                initial=field.default,
                label = self.get_field_label(field_name, field),
                choices=field.choices,
                help_text= self.get_field_help_text(field)
            )
        else:
            return forms.IntegerField(
                required=field.required,
                min_value=field.min_value,
                max_value=field.max_value,
                initial=field.default,
                label = self.get_field_label(field_name, field),
                help_text= self.get_field_help_text(field)
                )

    def generate_floatfield(self, field_name, field):

        form_class = forms.FloatField

        defaults = {'label': self.get_field_label(field_name, field),
                    'initial': field.default,
                    'required': field.required,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'help_text': self.get_field_help_text(field)}

        return form_class(**defaults)

    def generate_decimalfield(self, field_name, field):
        form_class = forms.DecimalField
        defaults = {'label': self.get_field_label(field_name, field),
                    'initial': field.default,
                    'required': field.required,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'help_text': self.get_field_help_text(field)}

        return form_class(**defaults)

    def generate_booleanfield(self, field_name, field):
        return forms.BooleanField(
            required=field.required,
            initial=field.default,
            label = self.get_field_label(field_name, field),
            help_text = self.get_field_help_text(field)
        )

    def generate_datetimefield(self, field_name, field):
        return forms.DateTimeField(
            required=field.required,
            initial=field.default,
            label = self.get_field_label(field_name, field),
        )

    def generate_referencefield(self, field_name, field):
        return ReferenceField(field.document_type.objects,
                              label = self.get_field_label(field_name, field),
                              help_text = self.get_field_help_text(field),
                              required=field.required)

    def generate_listfield(self, field_name, field):
        if field.field.choices:
            return forms.MultipleChoiceField(choices=field.field.choices,
                                             required=field.required,
                                             label = self.get_field_label(field_name, field),
                                             help_text = self.get_field_help_text(field),
                                             widget=forms.CheckboxSelectMultiple)
