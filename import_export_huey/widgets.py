from django import forms
from django.conf import settings


class CustomAjaxFileUploadWidget(forms.FileInput):
    template_name = 'custom_ajax_file_input.html'

    def value_from_datadict(self, data, files, name):
        file_path = data.get(name).replace(str(settings.MEDIA_ROOT), '')
        if file_path and file_path.startswith('/'):
            file_path = file_path[1:]
        return file_path
