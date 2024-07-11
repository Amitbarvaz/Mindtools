import re

from django.db.models import Q
from filer.models import File

from system.models import Content, Program, Session


class ProgramImportExportService:
    VARIABLE_PATTERN = r'\$\b[a-zA-Z0-9_]+\b'
    FILE_LIST_IDS_KEY = "file_list_ids"
    RELEVANT_VARIABLE_NAMES_LIST_KEY = "relevant_variable_names"

    def __init__(self, program: Program):
        self.program: Program = program
        self.main_data = self._init_main_data()

    @classmethod
    def export_program(cls, program):
        # Session Title is unique
        # Content Title is unique
        # Session - Content m2m holds data (unique)
        # Chapter Title is unique
        # Module Title is unique
        # Variable name is unique
        # Program title is unique
        # ProgramGoldVariable currently has no unique (prolly should be unique_together on program_id and variable_id)

        # TODO: How to handle files? (especially the dir structure)
        pass

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
        self.main_data[self.FILE_LIST_IDS_KEY].add(self.program.cover_image.id)
        file_list_ids = list(self.main_data[self.FILE_LIST_IDS_KEY])
        self.program.file_list_ids = file_list_ids

    def _annotate_with_variables(self):
        self.program.relevant_variables_names_list = self.main_data[self.RELEVANT_VARIABLE_NAMES_LIST_KEY]

    @classmethod
    def import_program(cls, program):
        pass
