import json
import logging
import re

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from filer.models import File, Folder, Image

from system.models import Chapter, Content, Module, Program, Session, Variable

class ProgramAfterImportRowHandler:

    def __init__(self, program: Program, row):
        self.program: Program = program
        self.objs_with_deferred_fields = []
        self.pk_mapping_dict = {"folders": {}, "files": {}}
        self.folder_fixtures = row.get("folders")
        self.file_fixtures = row.get("files")
        self.image_fixtures = row.get("images")
        self.variable_fixtures = row.get("variables")
        self.contents_fixtures = row.get("contents")
        self.session_fixtures = row.get("sessions")
        self.fixtures = [row.get("modules"), row.get("chapters"), row.get("gold_variables")]
        self.cover_image_sha1 = row.get("cover_image_sha1")
        self.format = "json"

    @transaction.atomic
    def import_program_data(self):
        self._handle_folder_fixtures()
        self._handle_file_fixtures()
        self._update_file_ids_in_contents()
        self.fixtures = [self.folder_fixtures, self.file_fixtures, self.image_fixtures, self.variable_fixtures,
                         self.contents_fixtures, self.session_fixtures] + self.fixtures

        self._switch_regular_signals()

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

        self._update_sessions_data_ref_id_and_url()
        self._switch_back_signals()

    @staticmethod
    def _switch_regular_signals():
        from django.db.models import signals
        from system.signals import content_post_save, add_content_relations, \
            decorated_add_content_relations, decorated_content_post_save
        logger.debug("Switching out regular signals")
        signals.post_save.disconnect(add_content_relations, sender=Session)
        signals.post_save.connect(decorated_add_content_relations, sender=Session)
        signals.post_save.disconnect(content_post_save)
        signals.post_save.connect(decorated_content_post_save)

    @staticmethod
    def _switch_back_signals():
        from django.db.models import signals
        from system.signals import content_post_save, add_content_relations, \
            decorated_add_content_relations, decorated_content_post_save
        logger.debug("Switching back regular signals")
        signals.post_save.disconnect(decorated_add_content_relations, sender=Session)
        signals.post_save.connect(add_content_relations, sender=Session)
        signals.post_save.disconnect(decorated_content_post_save)
        signals.post_save.connect(content_post_save)

    def _handle_folder_fixtures(self):
        logger.debug("Updating folder fixtures")
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
        logger.debug("Updating file fixtures")
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

    def _update_file_ids_in_contents(self):
        logger.debug("Updating file ids in contents")
        for content in self.contents_fixtures:
            def iterate_keys_and_values(data):
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict):
                            return iterate_keys_and_values(value)
                        elif key == "file_id" and value:
                            data[key] = self.pk_mapping_dict["files"][value]
                            # THINK ABOUT THIS TODO CUZ MAYBE THIS IS NOT NEEDED!
                            # TODO: handle url as well as file id // and maybe thumbnail as well...
                            #  and what should we do with thumbnails that don't have file id...
                elif isinstance(data, list):
                    for data_item in data:
                        iterate_keys_and_values(data_item)
                return

            for item in content["fields"].get("data", []):
                iterate_keys_and_values(item)

    def _update_sessions_data_ref_id_and_url(self):
        """
        Because we disconnected the signals we assume that the title is the unique id of each object
        """
        logger.debug("Updating session data ref_id and ref_url after import")
        sessions_titles = set()
        for session in self.session_fixtures:
            sessions_titles.add(session.get("fields", {}).get("title"))
        sessions = Session.objects.select_for_update(no_key=True).filter(title__in=list(sessions_titles))
        with transaction.atomic():
            for new_session in sessions:
                data = new_session.data
                nodes = data.get('nodes', [])
                for node in nodes:
                    title = node.get('title')
                    node_type = node.get('type')
                    if node_type in ['page', 'email', 'sms', 'session']:
                        try:
                            if node_type == 'session':
                                ref_object = Session.objects.get(title=title)
                            else:
                                ref_object = Content.objects.get(title=title)
                            node["ref_id"] = str(ref_object.id)
                            node["ref_url"] = re.sub(r'\d+', str(ref_object.id), node["ref_url"])
                        except (Session.DoesNotExist, Content.DoesNotExist):
                            node['title'] = f'ERROR IN IMPORT | OLD TITLE - {title}'
                            node['ref_id'] = f'ERROR IN IMPORT | OLD REF_ID - {node["ref_id"]}'
                            node['ref_url'] = f'ERROR IN IMPORT | OLD REF_URL - {node["ref_url"]}'

                data['nodes'] = nodes
                Session.objects.filter(id=new_session.id).update(data=data)


class ProgramBeforeImportRowHandler:
    """
    We run this to make sure natural keys or pks are unique, and to update all references
    """

    def __init__(self, row):
        self.row = row
        self.new_variable_name_suffix = row.get("title", "").replace(" ", "_") + "_New"

    def run(self):
        self._handle_program()
        self._handle_chapters()
        self._handle_modules()
        self._handle_variables()
        self._handle_contents()
        self._handle_sessions()
        return self.row

    def _handle_program(self):
        logger.debug("Handling program")
        if Program.objects.filter(title=self.row["title"]).exists():
            logger.debug(f"Program with title {self.row['title']} already exists, updating title")
            new_program_title = f"{self.row['title']} (new)"
            self.row["title"] = new_program_title
            self._iterate_data_and_update_key_with_value(
                ["chapters", "modules", "gold_variables", "sessions", "variables", "contents"], "program",
                new_program_title)

    def _handle_chapters(self):
        logger.debug("Handling chapters")
        for chapter in self.row["chapters"]:
            chapter_data = chapter["fields"]
            if Chapter.objects.filter(title=chapter_data["title"]).exists():
                logger.debug(f"Chapter with title {chapter_data['title']} already exists, updating title")
                new_chapter_title = f"{chapter_data['title']} (new)"
                chapter_data["title"] = new_chapter_title
                self._iterate_data_and_update_key_with_value(["contents"], "chapter", new_chapter_title)

    def _handle_modules(self):
        logger.debug("Handling modules")
        for module in self.row["modules"]:
            module_data = module["fields"]
            if Module.objects.filter(title=module_data["title"]).exists():
                logger.debug(f"Module with title {module_data['title']} already exists, updating title")
                new_module_title = f"{module_data['title']} (new)"
                module_data["title"] = new_module_title
                self._iterate_data_and_update_key_with_value(["chapters"], "module", new_module_title)

    def _handle_variables(self):
        logger.debug("Handling variables")
        for variable in self.row["variables"]:
            variable_data = variable["fields"]
            if Variable.objects.filter(name=variable_data["name"]).exists():
                logger.debug(f"Variable with name {variable_data['name']} already exists, updating name")
                old_variable_name = variable_data["name"]
                new_variable_name = f"{variable_data['name']}_{self.new_variable_name_suffix}"
                variable_data["name"] = new_variable_name
                self._iterate_data_and_update_key_with_value(["gold_variables"], "variable", new_variable_name)
                self._iterate_data_and_replace_old_value_with_new_value(["sessions", "contents"],
                                                                        ["variable", "expression", "value",
                                                                         "variable_name", "var_name", "content",
                                                                         "variables"],
                                                                        new_variable_name, old_variable_name)

    def _handle_contents(self):
        logger.debug("Handling contents")
        for content in self.row["contents"]:
            content_data = content["fields"]
            if Content.objects.filter(title=content_data["title"]).exists():
                logger.debug(f"Content with title {content_data['title']} already exists, updating title")
                old_content_title = content_data["title"]
                new_content_title = f"{content_data['title']}.New"
                content_data["title"] = new_content_title
                self._iterate_data_and_update_key_with_value(["sessions"], "content", new_content_title,
                                                             old_content_title)
                self._iterate_data_and_replace_old_value_with_new_value(["sessions"],
                                                                        ["title"],
                                                                        new_content_title, old_content_title,
                                                                        special_condition=["page", "sms", "email"])

    def _handle_sessions(self):
        logger.debug("Handling contents")
        for session in self.row["sessions"]:
            session_data = session["fields"]
            if Session.objects.filter(title=session_data["title"]).exists():
                logger.debug(f"Session with title {session_data['title']} already exists, updating title")
                old_session_title = session_data["title"]
                new_session_title = f"{session_data['title']} (new)"
                session_data["title"] = new_session_title
                self._iterate_data_and_update_key_with_value(["chapters"], "session", new_session_title)
                self._iterate_data_and_replace_old_value_with_new_value(["sessions"],
                                                                        ["title"],
                                                                        new_session_title, old_session_title,
                                                                        special_condition=["session"])

    def _iterate_data_and_update_key_with_value(self, row_keys, key, value, old_value=None):
        for row_key in row_keys:
            for item in self.row.get(row_key, []):
                item_contents = item.get(key, None)
                if item_contents is not None:
                    if isinstance(item_contents, list):
                        if any(isinstance(item_content, list) for item_content in item_contents):
                            new_item_contents = []
                            for item_content in item_contents:
                                if isinstance(item_content, list):
                                    temp = []
                                    for val in item_content:
                                        if val == old_value:
                                            temp.append(value)
                                        else:
                                            temp.append(val)
                                    new_item_contents.append(temp)
                                else:
                                    new_item_contents.append(item_content)
                            item[key] = new_item_contents
                        else:
                            item[key] = [value]
                    else:
                        item[key] = value

    def _iterate_data_and_replace_old_value_with_new_value(self, row_keys, dict_keys, new_value, old_value,
                                                           special_condition=None):
        """
        Special condition is for data in sessions where we want to check only specific titles (to add another condition), and not all
        """

        def iterate_keys_and_values(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        return iterate_keys_and_values(value)
                    elif key in dict_keys:
                        if ((special_condition is None or data.get("type", "") in special_condition)
                                and isinstance(data[key], str)):
                            data[key] = re.sub(r"\b%s\b" % old_value, new_value, data[key])
            elif isinstance(data, list):
                for data_item in data:
                    return iterate_keys_and_values(data_item)
            return

        for row_key in row_keys:
            for item in self.row.get(row_key, []):
                iterate_keys_and_values(item)
