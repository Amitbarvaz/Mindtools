from django.forms import ModelForm, fields
from django.utils.translation import gettext_lazy as _
from import_export.forms import ExportForm, ImportForm
from suit.widgets import AutosizedTextarea

from content.widgets import EmailDataContentWidget
from system.models import Email


class CustomEmailDataFormField(fields.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update({'widget': EmailDataContentWidget()})
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        content_value = super().to_python(value)
        return [{
            "content_type": "richtext",  # maybe should revert to text
            "content": content_value.replace("`", "'")  # this is a hacky way to protect the js
        }]


class EmailForm(ModelForm):
    data = CustomEmailDataFormField()

    def __init__(self, *args, **kwargs):
        super(EmailForm, self).__init__(*args, **kwargs)
        self.fields['data'].help_text = ''
        self.fields['display_title'].label = _('Subject')

    class Meta:
        model = Email
        fields = ['id', 'title', 'display_title', 'program', 'admin_note', 'data']
        widgets = {
            "admin_note": AutosizedTextarea(attrs={'rows': 3, 'class': 'input-xlarge'}),
        }


class ProgramExportForm(ExportForm):
    pass


class ProgramImportForm(ImportForm):
    pass
