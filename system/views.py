# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging
import re
import textwrap
from builtins import str

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework import viewsets
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from .filters import VariableSearchFilter
from .models import Program, Variable
from .serializers import ExpressionSerializer, VariableSerializer


@staff_member_required
def export_text(request):
    '''
    Iterates through all content in a Program and exports translatable text.
    TRANSLATION is a copy of ORIGINAL to help translators retain markdown
    and variable replacement syntax.
    '''

    ids = request.GET.getlist('ids')
    queryset = Program.objects.filter(id__in=ids)

    def indent(string):
        '''Helper for prettier code in format_field and format_content'''
        # Number of spaces in second param below should correspond
        # to indent in format_field() and format_content()
        return string.replace('\n', '\n            ')

    def format_field(obj, field):
        if not getattr(obj, field):
            return ''

        return textwrap.dedent('''\
            ///// %(model)s.%(id)i.%(field)s ORIGINAL
            %(value)s

            ///// %(model)s.%(id)i.%(field)s TRANSLATION
            %(value)s



            ''' % {
            'model': obj._meta.model_name,
            'id': obj.id,
            'field': field,
            'value': indent(getattr(obj, field)),
        })

    def format_content(obj, index, field, *fields, **kwargs):
        if not kwargs.get('value', '') and not obj.data[index].get(field):
            return ''

        return textwrap.dedent('''\
            ///// %(model)s.%(id)i.%(index)i.%(fields)s ORIGINAL
            %(value)s

            ///// %(model)s.%(id)i.%(index)i.%(fields)s TRANSLATION
            %(value)s



            ''' % {
            'model': obj._meta.model_name,
            'id': obj.id,
            'index': index,
            'fields': '.'.join([field] + list(fields)),
            'value': indent(kwargs.get('value', '')) or indent(obj.data[index].get(field)),
        })

    data = ''
    for program in queryset.order_by('id'):

        data += format_field(program, 'title')
        data += format_field(program, 'display_title')
        data += format_field(program, 'admin_note')

        for session in program.session_set.order_by('id'):

            data += format_field(session, 'title')
            data += format_field(session, 'display_title')
            data += format_field(session, 'admin_note')

            for content in session.content.order_by('id'):
                for index, pagelet in enumerate(content.data):

                    if pagelet['content_type'] == 'text':
                        data += format_content(content, index, 'content')

                    if pagelet['content_type'] == 'toggle':
                        data += format_content(content, index, 'content')
                        data += format_content(content, index, 'toggle')

                    if pagelet['content_type'] in ['toggleset', 'togglesetmulti']:
                        data += format_content(content, index, 'content', 'label', value=pagelet['content']['label'])

                        for i, item in enumerate(pagelet['content']['alternatives']):
                            data += format_content(content, index, 'content', 'alternatives', str(i), 'label',
                                                   value=item['label'])
                            data += format_content(content, index, 'content', 'alternatives', str(i), 'text',
                                                   value=item['text'])

                    if pagelet['content_type'] == 'conditionalset':
                        for i, item in enumerate(pagelet['content']):
                            data += format_content(content, index, 'content', str(i), 'content', value=item['content'])

                    if pagelet['content_type'] == 'form':
                        for i, item in enumerate(pagelet['content']):

                            if item['field_type'] in ['numeric', 'string', 'text']:
                                data += format_content(content, index, 'content', str(i), 'label',
                                                       value=item['label'] or ' ')

                            if item['field_type'] == 'multiplechoice':
                                data += format_content(content, index, 'content', str(i), 'label',
                                                       value=item['label'] or ' ')
                                for j, alt in enumerate(item['alternatives']):
                                    data += format_content(content, index, 'content', str(i), 'alternatives', str(j),
                                                           'label', value=alt['label'])

                            if item['field_type'] == 'multipleselection':
                                data += format_content(content, index, 'content', str(i), 'label',
                                                       value=item['label'] or ' ')
                                for j, alt in enumerate(item['alternatives']):
                                    data += format_content(content, index, 'content', str(i), 'alternatives', str(j),
                                                           'label', value=alt['label'])

                    if pagelet['content_type'] == 'quiz':
                        for i, item in enumerate(pagelet['content']):
                            data += format_content(content, index, 'content', str(i), 'question',
                                                   value=item['question'])
                            data += format_content(content, index, 'content', str(i), 'right', value=item['right'])
                            data += format_content(content, index, 'content', str(i), 'wrong', value=item['wrong'])

                            for j, alt in enumerate(item['alternatives']):
                                data += format_content(content, index, 'content', str(i), 'alternatives', str(j),
                                                       'label', value=alt['label'])

        # Variables should be included if translation of name, display_name, value etc. are needed
        # this requires corresponding routines to copy Variables on Program copy

        # for variable in program.variable_set.order_by('id'):
        #     data += format_field(variable, 'name')
        #     data += format_field(variable, 'display_name')
        #     data += format_field(variable, 'admin_note')
        #     data += format_field(variable, 'value')
        #     data += format_field(variable, 'random_set')

    response = HttpResponse(data, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=text_content.md'

    return response


@staff_member_required
def import_text(request):
    '''
    Finds all TRANSLATION sections from a text file as exported by export_text(),
    extracts models, ids and field identifiers, and updates the given text.
    '''

    def drilldown_assign(obj, keys, value):
        '''
        Recursively drills down through a nested data structure by a
        given list of keys or list indices, and sets a value, leaving the
        data structure otherwise intact
        '''
        if not keys:
            obj = value
        else:
            try:
                keys[0] = int(keys[0])
            except:
                pass
            obj[keys[0]] = drilldown_assign(obj[keys[0]], keys[1:], value)
        return obj

    redirect = request.GET.get('next')

    if request.method == 'POST':

        text = request.FILES.get('text')

        matches = re.findall(
            '///// (\w+).(\d+).([\w\d.]+) TRANSLATION\n(.+?)\n\n\n',
            text.read(),
            re.DOTALL | re.UNICODE
        )

        for model, obj_id, identifier, value in matches:

            ct = ContentType.objects.get(app_label='system', model=model)
            obj = ct.get_object_for_this_type(id=obj_id)

            keys = identifier.split('.')

            update_kwargs = {}

            if len(keys) == 1:
                update_kwargs[identifier] = value

            elif len(keys) > 1:
                drilldown_assign(obj.data, keys, value)
                update_kwargs['data'] = obj.data

            # update database
            type(obj).objects.filter(id=obj_id).update(**update_kwargs)

        return HttpResponseRedirect(redirect)

    return render(request, 'import_text.html', {})


@staff_member_required
def set_program(request):
    """
    View for setting the current working program.
    Pretty much copied from the set_language view.
    """
    redirect_to = request.POST.get("next", request.GET.get("next"))
    if not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=[request.get_host()]):
        redirect_to = request.META.get("HTTP_REFERER")
        if not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=[request.get_host()]):
            redirect_to = "/"
    response = HttpResponseRedirect(redirect_to)
    if request.method == "POST":
        program_id = request.POST.get("program", None)
        if program_id and Program.objects.filter(pk=program_id).exists():
            if hasattr(request, "session"):
                request.session["_program_id"] = program_id
        elif program_id == "-1":
            if hasattr(request, "session") and "_program_id" in request.session:
                del request.session["_program_id"]
    return response


@staff_member_required
def set_stylesheet(request):
    """
    View for setting a stylesheet in a session variable.
    Use a template tag to check for the existence of the
    stylesheet and use it if existing.
    """
    redirect_to = request.POST.get("next", request.GET.get("next"))
    if not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=[request.get_host()]):
        redirect_to = request.META.get("HTTP_REFERER")
        if not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=[request.get_host()]):
            redirect_to = "/"
    response = HttpResponseRedirect(redirect_to)
    if request.method == "POST":
        stylesheet = request.POST.get("stylesheet", None)
        if stylesheet and stylesheet in [s["name"] for s in getattr(settings, "STYLESHEETS", [])]:
            if hasattr(request, "session"):
                request.session["_stylesheet"] = stylesheet
        elif not stylesheet:
            if hasattr(request, "session") and "_stylesheet" in request.session:
                del request.session["_stylesheet"]
    return response


def redirect_media(request, path):
    return HttpResponseRedirect(
        'https://s3.eu-central-1.amazonaws.com/%s/%s' % (settings.AWS_STORAGE_BUCKET_NAME, path))


class VariableViewSet(viewsets.ModelViewSet):
    queryset = Variable.objects.all().order_by("name")
    serializer_class = VariableSerializer

    def get_queryset(self):
        if '_program_id' in self.request.session:
            queryset = self.queryset.filter(program__id=self.request.session['_program_id'])
            return queryset
        elif not self.request.user.is_superuser and self.request.user.program_restrictions.exists():
            queryset = self.queryset.filter(program=self.request.user.program_restrictions.first())
            return queryset

        return self.queryset


class VariableSearchViewSet(viewsets.ModelViewSet):
    queryset = Variable.objects.all().order_by("name")
    serializer_class = VariableSerializer
    filter_backends = [VariableSearchFilter]
    search_fields = ["name", "display_name"]

    def get_queryset(self):
        """
        Should only return variables for the currently working
        program if any.
        """
        queryset = super(VariableSearchViewSet, self).get_queryset()
        if '_program_id' in self.request.session:
            queryset = queryset.filter(program__id=self.request.session['_program_id'])
        return queryset

    def list(self, request, *args, **kwargs):
        """
        Add system variables to search results
        """
        response = super(VariableSearchViewSet, self).list(request, *args, **kwargs)
        reserved_variables = [v for v in getattr(settings, "RESERVED_VARIABLES", {})
                              if "domains" in v and "user" in v["domains"]]
        response.data.extend(reserved_variables)
        return response


class ExpressionViewSet(CreateModelMixin, viewsets.ViewSet):
    """
    API resource for evaluating expressions.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ExpressionSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.serializer_class
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)


@staff_member_required
def handle_ajax_file_upload(request):
    if request.method == 'POST':
        file = request.FILES['file'].read()
        fileName = request.POST['filename']
        existingPath = request.POST['existingPath']
        end = bool(int(request.POST['end']))
        nextSlice = request.POST['nextSlice']

        if file == "" or fileName == "" or existingPath == "" or end == "" or nextSlice == "":
            res = JsonResponse({'data': 'Invalid Request'})
            return res
        else:
            if existingPath == 'null':
                logger = logging.getLogger("debug")
                path = os.path.join(settings.MEDIA_ROOT, "django-import-export-huey-import-jobs", f'{timezone.now().strftime("%Y%m%d%H%M%S")}_{fileName}')
                logger.debug(f"uploading file to {path}")
                with open(path, 'wb+') as destination:
                    destination.write(file)

                cache.set(path.replace(" ", "_"), {"name": fileName, "eof": end})
                if end:
                    res = JsonResponse({'data': 'Uploaded Successfully', 'existingPath': path})
                else:
                    res = JsonResponse({'existingPath': path})
                return res

            else:
                file_cached_data = cache.get(existingPath.replace(" ", "_"))
                if file_cached_data.get("name") == fileName:
                    if not file_cached_data.get("eof"):
                        with open(existingPath, 'ab+') as destination:
                            destination.write(file)
                        if end:
                            cache.set(str(existingPath), {"name": fileName, "eof": end})
                            res = JsonResponse(
                                {'data': 'Uploaded Successfully', 'existingPath': existingPath})
                        else:
                            res = JsonResponse({'existingPath': existingPath})
                        return res
                    else:
                        res = JsonResponse({'data': 'EOF found. Invalid request'})
                        return res
                else:
                    res = JsonResponse({'data': 'No such file exists in the existingPath'})
                    return res
    return redirect(reverse("admin:import_export_huey_importjob_changelist"))
