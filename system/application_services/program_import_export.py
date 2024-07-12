import json
import re

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import IntegrityError, transaction
from django.db.models import Q
from filer.models import File, Folder, Image

from system.models import Content, Program, Session


class ProgramExportService:
    VARIABLE_PATTERN = r'\$\b[a-zA-Z0-9_]+\b'
    FILE_LIST_IDS_KEY = "file_list_ids"
    RELEVANT_VARIABLE_NAMES_LIST_KEY = "relevant_variable_names"

    def __init__(self, program: Program):
        self.program: Program = program
        self.main_data = self._init_main_data()

    def annotate_program_instance_for_export(self):
        self._annotate_with_files()
        self._annotate_with_variables()
        return self.program

    def _init_main_data(self):

        main_data = {
            self.FILE_LIST_IDS_KEY: set(),
            self.RELEVANT_VARIABLE_NAMES_LIST_KEY: set()
        }

        def extract_data_from_content_dicts(temp_data):
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

        for content in Content.objects.filter(Q(session__program=self.program) | Q(program=self.program)).distinct():
            for data in content.data:
                extract_data_from_content_dicts(data)

        def extract_data_from_session_dicts(temp_data):
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
            for node in session.data.get("nodes"):
                extract_data_from_session_dicts(node)
            for edge in session.data.get("edges"):
                extract_data_from_session_dicts(edge)
        return main_data

    def _annotate_with_files(self):
        if self.program.cover_image:
            self.main_data[self.FILE_LIST_IDS_KEY].add(self.program.cover_image.id)
        file_list_ids = list(self.main_data[self.FILE_LIST_IDS_KEY])
        self.program.file_list_ids = file_list_ids

    def _annotate_with_variables(self):
        self.program.relevant_variables_names_list = self.main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY]


class ProgramImportService:

    def __init__(self, program: Program, row):
        self.program: Program = program
        self.objs_with_deferred_fields = []
        self.pk_mapping_dict = {"folders": {}, "files": {}}
        self.folder_fixtures = row.get("folders")
        self.file_fixtures = row.get("files")
        self.image_fixtures = row.get("images")
        self.fixtures = [row.get("variables"), row.get("contents"), row.get("sessions"), row.get("modules"),
                         row.get("chapters"), row.get("gold_variables")]
        self.cover_image_sha1 = row.get("cover_image_sha1")
        self.format = "json"

    @transaction.atomic
    def import_program_data(self):
        self._handle_folder_fixtures()
        self._handle_file_fixtures()

        self.fixtures = [self.folder_fixtures, self.file_fixtures, self.image_fixtures] + self.fixtures

        for fixture in self.fixtures:
            objects = serializers.deserialize(
                self.format,
                json.dumps(fixture),
                handle_forward_references=True,
            )
            for obj in objects:
                obj.save()
                if obj.deferred_fields:
                    self.objs_with_deferred_fields.append(obj)
        for obj in self.objs_with_deferred_fields:
            obj.save_deferred_fields()

        img = Image.objects.filter(sha1=self.cover_image_sha1).first()
        self.program.cover_image = img
        self.program.save()

    def _handle_folder_fixtures(self):
        latest_folder_pk = 1
        latest_folder = Folder.objects.latest("pk")
        if latest_folder:
            latest_folder_pk = latest_folder.pk + 1
        for folder in self.folder_fixtures:
            self.pk_mapping_dict["folders"][folder.get("pk")] = latest_folder_pk
            folder["pk"] = latest_folder_pk
            latest_folder_pk += 1
        for folder in self.folder_fixtures:
            parent_folder_pk = folder.get("fields", {}).get("parent")
            if parent_folder_pk:
                folder["fields"]["parent"] = self.pk_mapping_dict["folders"][parent_folder_pk]

    def _handle_file_fixtures(self):
        image_ctype = ContentType.objects.get_for_model(Image)
        file_ctype = ContentType.objects.get_for_model(File)
        image_ids = [image["pk"] for image in self.image_fixtures]

        latest_file_pk = 1
        latest_file = File.objects.latest("pk")
        if latest_file:
            latest_file_pk = latest_file.pk + 1

        for file in self.file_fixtures:
            file["fields"]["polymorphic_ctype"] = image_ctype.pk if file["pk"] in image_ids else file_ctype.pk
            if file["fields"]["folder"]:
                file["fields"]["folder"] = self.pk_mapping_dict["folders"][file["fields"]["folder"]]
            self.pk_mapping_dict["files"][file["pk"]] = latest_file_pk
            file["pk"] = latest_file_pk
            latest_file_pk += 1

        for image in self.image_fixtures:
            image["pk"] = self.pk_mapping_dict["files"][image["pk"]]

    @classmethod
    def move_auto_increment_pointers(cls):
        """
        Because we are manually playing with the pks in the images and folders we need to force update
        their autoincrement counters
        """
        while True:
            try:
                folder = Folder.objects.create(name="test")
            except IntegrityError:
                continue
            else:
                folder.delete()
                break

        while True:
            try:
                image = Image.objects.create()
            except IntegrityError:
                continue
            else:
                image.delete()
                break
