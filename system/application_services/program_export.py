import json
import logging
import re

from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q, QuerySet
from filer.models import File, Folder, Image

from system.models import Chapter, Content, Program, ProgramGoldVariable, Session, Variable

logger = logging.getLogger("debug")


class ProgramExportHandler:
    """
    This helps prepare data for export by annotating that program with some id list for filtering on dehydration in
    export resource.
    """
    VARIABLE_PATTERN = r'\$\b[a-zA-Z0-9_]+\b'
    VARIABLE_PATTERN_INSIDE_CONTENT = r'\{\{\s*[a-zA-Z0-9_]+\s*\}\}'
    FILE_LIST_IDS_KEY = "file_list_ids"
    RELEVANT_VARIABLE_NAMES_LIST_KEY = "relevant_variable_names"

    def __init__(self, program: Program, file_path: str):
        self.program: Program = program
        self.file_path = file_path
        self.stream = None
        self.main_data = self._init_main_data()
        self.json_kwargs = {
            "cls": DjangoJSONEncoder,
            "ensure_ascii": False
        }

    def export(self):
        logger.debug("Starting export")
        logging.getLogger("huey").info("Starting export")
        with open(self.file_path, "w", encoding="utf-8") as file:
            self.stream = file
            self._start_serialization()
            self._export_program_data()
            self._export_sessions()
            self._export_chapters()
            self._export_modules()
            self._export_variables()
            self._export_contents()
            self._export_images()
            self._export_files()
            self._export_folders()
            self._export_gold_variables()
            self._end_serialization()
        logger.debug("Finished export")
        logging.getLogger("huey").info("Finished export")

    def _export_program_data(self):
        self._start_object("program")
        data = {
            "title": self.program.title,
            "display_title": self.program.display_title,
            "about": self.program.about,
            "style": self.program.style,
            "admin_note": self.program.admin_note,
            "is_lock": self.program.is_lock,
            "default_program_start_time": self.program.default_program_start_time,
            "cover_image_sha1": self.program.cover_image.sha1 if self.program.cover_image else ""
        }
        self._manually_write_to_stream(data)
        self._end_object()

    def _export_sessions(self):
        self._start_object("sessions")
        serializers.serialize('json', self.program.session_set.all(), stream=self.stream,
                              use_natural_primary_keys=True, use_natural_foreign_keys=True)
        self._end_object()

    def _export_chapters(self):
        self._start_object("chapters")
        qs = Chapter.objects.filter(Q(id__in=self.program.chapter_set.values_list("id", flat=True)) | Q(
            id__in=self.program.module_set.values_list("chapter", flat=True)) | Q(
            id__in=Content.objects.filter(Q(program=self.program) | Q(session__program=self.program)).values_list(
                "chapter", flat=True)
        )).distinct()
        serializers.serialize('json', qs, stream=self.stream, use_natural_primary_keys=True,
                              use_natural_foreign_keys=True)
        self._end_object()

    def _export_modules(self):
        self._start_object("modules")
        serializers.serialize('json', self.program.module_set.all(), stream=self.stream,
                              use_natural_primary_keys=True, use_natural_foreign_keys=True)
        self._end_object()

    def _export_variables(self):
        self._start_object("variables")
        qs = Variable.objects.filter(name__in=self.main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY]).distinct()
        data = json.loads(
            serializers.serialize('json', qs, use_natural_primary_keys=True, use_natural_foreign_keys=True))
        for item in data:
            if "program" in item["fields"]:
                item["fields"]["program"] = self.program.natural_key()
        self._manually_write_to_stream(data)
        self._end_object()

    def _export_contents(self):
        self._start_object("contents")
        qs = Content.objects.filter(Q(program=self.program) | Q(session__program=self.program)).distinct()
        serializers.serialize('json', qs, stream=self.stream,
                              use_natural_primary_keys=True, use_natural_foreign_keys=True)
        self._end_object()

    def _export_images(self):
        self._start_object("images")
        qs = Image.objects.filter(id__in=self.main_data[self.FILE_LIST_IDS_KEY]).distinct()
        serializers.serialize('json', qs, stream=self.stream)
        self._end_object()

    def _export_files(self):
        self._start_object("files")
        klass = File
        klass.objects.queryset_class = QuerySet
        qs = klass.objects.filter(id__in=self.main_data[self.FILE_LIST_IDS_KEY]).distinct()
        serializers.serialize('json', qs, stream=self.stream)
        self._end_object()

    def _export_folders(self):
        self._start_object("folders")
        qs = Folder.objects.filter(all_files__id__in=self.main_data[self.FILE_LIST_IDS_KEY])
        parent_folders = qs.values_list('parent', flat=True)
        qs = Folder.objects.filter(
            Q(id__in=parent_folders) | Q(all_files__id__in=self.main_data[self.FILE_LIST_IDS_KEY])).distinct()
        serializers.serialize('json', qs, stream=self.stream)
        self._end_object()

    def _export_gold_variables(self):
        self._start_object("gold_variables")
        qs = ProgramGoldVariable.objects.filter(program=self.program).distinct()
        serializers.serialize('json', qs, stream=self.stream,
                              use_natural_primary_keys=True, use_natural_foreign_keys=True)
        self._end_object(last_object=True)

    def _start_serialization(self):
        self.stream.write("{")

    def _end_serialization(self):
        self.stream.write("}")

    def _start_object(self, object_name: str):
        self.stream.write(f'"{object_name}": ')

    def _end_object(self, last_object: bool = False):
        if not last_object:
            self.stream.write(', ')

    def _manually_write_to_stream(self, data):
        json.dump(data, self.stream, **self.json_kwargs)

    def _init_main_data(self):
        main_data = {
            self.FILE_LIST_IDS_KEY: set(),
            self.RELEVANT_VARIABLE_NAMES_LIST_KEY: set()
        }

        def extract_data_from_content_dicts(temp_data):
            """
            This method extracts data from content data dictionaries by iterating over them recursively.
            When it finds something that resembles a file or variable it adds it to the main dictionary
            """
            for key, value in temp_data.items():
                if isinstance(value, dict):
                    return extract_data_from_content_dicts(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            return extract_data_from_content_dicts(item)
                        else:
                            return extract_data_from_content_dicts({key: item})
                elif key == "file_id" and value:
                    main_data[self.FILE_LIST_IDS_KEY].add(int(value))
                    return
                elif key in ["variable_name", "var_name"]:
                    main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(value)
                elif key == "variables" and isinstance(temp_data[key], dict):
                    for variable in temp_data[key].keys():
                        main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(variable)
                elif key == "expression" or (key in ["value", "content"] and isinstance(value, str)):
                    for match in re.findall(self.VARIABLE_PATTERN, value):
                        main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(match.replace("$", ""))
                    for match in re.findall(self.VARIABLE_PATTERN_INSIDE_CONTENT, value):
                        main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(
                            match.replace("{", "").replace("}", "").strip())

        for content in Content.objects.filter(Q(session__program=self.program) | Q(program=self.program)).distinct():
            logger.debug(f"Extracting data from content: {content.title}")
            for data in content.data:
                extract_data_from_content_dicts(data)

        def extract_data_from_session_dicts(temp_data):
            """
            This method extracts data from session data dictionaries by iterating over them recursively.
            When it finds something that resembles a variable it adds it to the main dictionary
            """
            for key, value in temp_data.items():
                if isinstance(value, dict):
                    return extract_data_from_session_dicts(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            return extract_data_from_session_dicts(item)
                        else:
                            return extract_data_from_session_dicts({key: item})
                elif key in ["variable_name", "var_name", "variable"]:
                    main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(value)
                elif key == "variables" and isinstance(temp_data[key], dict):
                    for variable in temp_data[key].keys():
                        main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(variable)
                elif key == "expression":
                    for match in re.findall(self.VARIABLE_PATTERN, value):
                        main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY].add(match.replace("$", ""))

        for session in Session.objects.filter(Q(program=self.program)):
            logger.debug(f"Extracting data from session: {session.title}")
            for node in session.data.get("nodes"):
                extract_data_from_session_dicts(node)
            for edge in session.data.get("edges"):
                extract_data_from_session_dicts(edge)
        if self.program.cover_image:
            main_data[self.FILE_LIST_IDS_KEY].add(self.program.cover_image.id)
        main_data[self.FILE_LIST_IDS_KEY] = list(main_data[self.FILE_LIST_IDS_KEY])
        main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY] = list(main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY])
        return main_data
