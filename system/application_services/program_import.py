import json
import logging
import re
from sys import getsizeof
from typing import Union

import ijson
import psutil
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections, router, transaction
from django.db.transaction import set_rollback
from filer.models import File, Folder, Image

from system.models import Chapter, Content, Email, Module, Page, Program, SMS, Session, Variable

logger = logging.getLogger("debug")


class NotEnoughMemory(Exception):
    pass


class ProgramImportHandler:
    CHAPTERS = "chapters"
    MODULES = "modules"
    SESSIONS = "sessions"
    VARIABLES = "variables"
    CONTENTS = "contents"
    FOLDERS = "folders"
    IMAGES = "images"
    PROGRAM = "program"
    FILES = "files"
    GOLD_VARIABLES = "gold_variables"

    def __init__(self, import_file_path):
        self.file_path = import_file_path
        self.program_fixture = []
        self.program_data = {}
        self.sessions_fixtures = []
        self.contents_fixtures = []
        self.variables_fixtures = []
        self.folders_fixtures = []
        self.images_fixtures = []
        self.modules_fixtures = []
        self.chapters_fixtures = []
        self.gold_variables_fixtures = []
        self.cover_image_sha1 = ""
        self.objs_with_deferred_fields = []
        self.file_ids_with_deferred_fields = []
        self.pk_mapping_dict = {self.FOLDERS: {}, self.FILES: {}}
        self.program: Union[Program, None] = None
        self.format = "json"
        self.fixtures = []
        self.signals_not_switched_back: bool = False
        self.non_file_keys = [self.CHAPTERS, self.MODULES, self.SESSIONS, self.VARIABLES, self.MODULES, self.CONTENTS,
                              self.FOLDERS, self.IMAGES, self.GOLD_VARIABLES]
        self.new_variable_name_suffix = ""
        # todo - think about adding a validation step for keys inside file... (to check all fixtures exist /
        #  file structure is correct)

    def run_import(self, dry_run=True):
        db_connection = router.db_for_write(Program)
        connection = connections[db_connection]

        # We force using transactions here (postgresql only support currently)
        supports_transactions = getattr(
            connection.features, "supports_transactions", False
        )
        if not supports_transactions:
            logger.exception(ImproperlyConfigured)
            raise ImproperlyConfigured

        with transaction.atomic(using=db_connection):
            try:
                self._verify_system_has_enough_memory()
                self._load_data_into_memory()
                self._handle_data_before_import()
                self._import_data()
                self._handle_data_after_import()
            except Exception as e:
                set_rollback(True, using=db_connection)
                if self.signals_not_switched_back:
                    self._switch_back_signals()
                logger.exception(e)
                raise e
            else:
                logger.debug("Import Succeeded")
                if dry_run:
                    set_rollback(True, using=db_connection)
                return "Successfully imported program"

    def _verify_system_has_enough_memory(self):
        """
        We currently need to load all keys into memory except files in this implementation
        So we check we can do this while loading the largest file into memory, with a buffer
        This is very naive as we don't account for all memory, but only available memory in a specific time
        """
        logger.debug("Verifying enough memory for process")
        available_memory = psutil.virtual_memory().available
        approx_total_size_except_files = 0
        for key in self.non_file_keys:
            with open(self.file_path, "r") as file:
                objects = ijson.items(file, f"{key}.item")
                for obj in objects:
                    approx_total_size_except_files += sum(getsizeof(i) for i in obj.get("fields", {}).values())
        file_sizes = []
        with open(self.file_path, "r") as file:
            objects = ijson.items(file, "files.item")
            for obj in objects:
                file_sizes.append(int(obj.get("fields", {}).get("_file_size", 0)))
        max_file_size = max(file_sizes)
        buffer = (max_file_size + approx_total_size_except_files) * 0.05
        if max_file_size + approx_total_size_except_files + buffer > available_memory:
            raise NotEnoughMemory(f"Current implementation requires more memory than available: "
                                  f"{max_file_size + approx_total_size_except_files + buffer} needed, {available_memory}"
                                  f" available\nTotal memory is {psutil.virtual_memory().total} bytes")

    def _load_data_into_memory(self):
        logger.debug("Loading data into memory")
        with open(self.file_path, "r") as file:
            self.program_data = list(ijson.items(file, self.PROGRAM))[0]
        self.cover_image_sha1 = self.program_data.pop("cover_image_sha1", "")
        self.program_fixture = [{
            "model": f"{Program._meta.app_label}.{Program._meta.model_name}",
            "fields": self.program_data
        }]
        for key in self.non_file_keys:
            with open(self.file_path, "r") as file:
                setattr(self, f"{key}_fixtures", list(ijson.items(file, f"{key}.item")))
        self.new_variable_name_suffix = self.program_data.get("title", "").replace(" ", "_") + "_New"

    def _handle_data_before_import(self):
        self._handle_program()
        self._handle_chapters()
        self._handle_modules()
        self._handle_variables()
        self._handle_contents()
        self._handle_sessions()

    @transaction.atomic
    def _import_data(self):
        deserialized_programs = serializers.deserialize(self.format,
                                                        json.dumps(self.program_fixture, cls=DjangoJSONEncoder,
                                                                   ensure_ascii=False))
        self.program = next(deserialized_programs)
        self.program.save()
        self._handle_folders_fixtures()
        self._handle_file_fixtures()
        self._update_file_ids_in_contents()
        self.fixtures = [self.images_fixtures, self.variables_fixtures, self.contents_fixtures, self.sessions_fixtures,
                         self.modules_fixtures, self.chapters_fixtures, self.gold_variables_fixtures]

        self._switch_regular_signals()

        for fixture in self.fixtures:
            logger.debug(f"Deserializing fixture {fixture[0].get('model') if len(fixture) > 0 else None}")
            objects = serializers.deserialize(
                self.format,
                json.dumps(fixture, cls=DjangoJSONEncoder, ensure_ascii=False),
                handle_forward_references=True,
            )
            for obj in objects:
                obj.save()
                if obj.deferred_fields:
                    self.objs_with_deferred_fields.append(obj)
        for obj in self.objs_with_deferred_fields:
            obj.save_deferred_fields()

    def _handle_data_after_import(self):
        self._handle_deferred_fields_for_files()
        img = Image.objects.filter(sha1=self.cover_image_sha1).first()
        if img:
            self.program.cover_image = img
            self.program.save()

        self._update_sessions_data_ref_id_and_url()
        self._switch_back_signals()
        self._trigger_content_post_save_for_each_content()

    def _handle_program(self):
        logger.debug("Handling program data before import")
        if Program.objects.filter(title=self.program_data["title"]).exists():
            logger.debug(f"Program with title {self.program_data['title']} already exists, updating title")
            new_program_title = f"{self.program_data['title']} (new)"
            self.program_data["title"] = new_program_title
            # Here we assume that there is only 1 relevant program for all the different data to be related to
            self._iterate_dict_keys_and_update_key_with_value([self.CHAPTERS, self.MODULES, self.GOLD_VARIABLES,
                                                               self.SESSIONS, self.VARIABLES, self.CONTENTS], "program",
                                                              new_program_title)

    def _handle_chapters(self):
        logger.debug("Handling chapters data before import")
        for chapter in self.chapters_fixtures:
            chapter_data = chapter["fields"]
            if Chapter.objects.filter(title=chapter_data["title"]).exists():
                old_chapter_title = chapter_data["title"]
                logger.debug(f"Chapter with title {old_chapter_title} already exists, updating title")
                new_chapter_title = f"{old_chapter_title} (new)"
                chapter_data["title"] = new_chapter_title
                self._iterate_dict_keys_and_update_key_with_value([self.CONTENTS], "chapter",
                                                                  new_chapter_title, old_chapter_title)

    def _handle_modules(self):
        logger.debug("Handling modules data before import")
        for module in self.modules_fixtures:
            module_data = module["fields"]
            if Module.objects.filter(title=module_data["title"]).exists():
                old_module_title = module_data["title"]
                logger.debug(f"Module with title {old_module_title} already exists, updating title")
                new_module_title = f"{old_module_title} (new)"
                module_data["title"] = new_module_title
                self._iterate_dict_keys_and_update_key_with_value([self.CHAPTERS], "module",
                                                                  new_module_title, old_module_title)

    def _handle_variables(self):
        logger.debug("Handling variables data before import")
        for variable in self.variables_fixtures:
            variable_data = variable["fields"]
            if Variable.objects.filter(name=variable_data["name"]).exists():
                old_variable_name = variable_data["name"]
                logger.debug(f"Variable with name {old_variable_name} already exists, updating name")
                new_variable_name = f"{old_variable_name}_{self.new_variable_name_suffix}"
                variable_data["name"] = new_variable_name
                self._iterate_dict_keys_and_update_key_with_value([self.GOLD_VARIABLES], "variable",
                                                                  new_variable_name, old_variable_name)
                self._iterate_data_and_replace_old_value_with_new_value([self.SESSIONS, self.CONTENTS],
                                                                        ["variable", "expression", "value",
                                                                         "variable_name", "var_name", "content",
                                                                         "variables"],
                                                                        new_variable_name, old_variable_name)

    def _handle_contents(self):
        logger.debug("Handling contents data before import")
        for content in self.contents_fixtures:
            content_data = content["fields"]
            if Content.objects.filter(title=content_data["title"]).exists():
                old_content_title = content_data["title"]
                logger.debug(f"Content with title {old_content_title} already exists, updating title")
                new_content_title = f"{old_content_title}.New"
                content_data["title"] = new_content_title
                self._iterate_dict_keys_and_update_key_with_value([self.SESSIONS], "content",
                                                                  new_content_title, old_content_title)
                self._iterate_data_and_replace_old_value_with_new_value([self.SESSIONS],
                                                                        [],
                                                                        new_content_title, old_content_title,
                                                                        special_condition=["page", "sms", "email"])

    def _handle_sessions(self):
        logger.debug("Handling sessions data before import")
        for session in self.sessions_fixtures:
            session_data = session["fields"]
            if Session.objects.filter(title=session_data["title"]).exists():
                old_session_title = session_data["title"]
                logger.debug(f"Session with title {old_session_title} already exists, updating title")
                new_session_title = f"{old_session_title} (new)"
                session_data["title"] = new_session_title
                self._iterate_dict_keys_and_update_key_with_value([self.CHAPTERS], "session",
                                                                  new_session_title, old_session_title)
                self._iterate_data_and_replace_old_value_with_new_value([self.SESSIONS],
                                                                        [],
                                                                        new_session_title, old_session_title,
                                                                        special_condition=["session"])
            if session_data.get("route_slug", None) is not None:
                session_data["route_slug"] = (f"{session_data['route_slug']}-"
                                              f"{self.new_variable_name_suffix.replace('_', '-')}")

    def _iterate_dict_keys_and_update_key_with_value(self, fixture_keys, key, new_value, old_value=None):
        for fixture_key in fixture_keys:
            for item in getattr(self, f"{fixture_key}_fixtures", []):
                if "fields" in item:
                    item_data = item["fields"]
                else:
                    item_data = item
                item_contents = item_data.get(key, None)
                if item_contents is not None:
                    if isinstance(item_contents, list):
                        new_item_contents = []
                        for item_content in item_contents:
                            if isinstance(item_content, list):
                                temp = []
                                for val in item_content:
                                    if val == old_value:
                                        temp.append(new_value)
                                    else:
                                        temp.append(val)
                                new_item_contents.append(temp)
                            elif old_value is None or item_content == old_value:
                                new_item_contents.append(new_value)
                            else:
                                new_item_contents.append(item_content)
                        item_data[key] = new_item_contents
                    elif old_value is None or item_data[key] == old_value:
                        item_data[key] = new_value

    def _iterate_data_and_replace_old_value_with_new_value(self, fixture_keys, dict_keys, new_value, old_value,
                                                           special_condition=None):
        """
        We chose not to use recursion to be more verbose
        1. go into the fixture and load the data as a python object
        2. generate copies, edit them using conditions
        3. dump the data to string into the fixture loaded to memory
        """
        for fixture_key in fixture_keys:
            for item in getattr(self, f"{fixture_key}_fixtures", []):
                item_data = item.get("fields", {}).get("data", None)
                if item_data is not None:
                    temp_item_data = json.loads(item_data)
                    if fixture_key == self.SESSIONS:
                        special_condition = [] if special_condition is None else special_condition
                        temp_nodes_data = []
                        for node in temp_item_data["nodes"]:
                            node_copy = node.copy()
                            if (node_copy.get("type", "") in special_condition and
                                    node_copy.get("title", "") == old_value):
                                node_copy["title"] = new_value
                            for key in dict_keys:
                                if key in node:
                                    node_copy[key] = re.sub(r"\b%s\b" % old_value, new_value, node[key])
                            temp_nodes_data.append(node_copy)
                        temp_item_data["nodes"] = temp_nodes_data

                        temp_edges_data = []
                        for edge in temp_item_data["edges"]:
                            edge_copy = edge.copy()
                            if "expression" in edge:
                                edge_copy["expression"] = re.sub(r"\b%s\b" % old_value, new_value, edge["expression"])
                            if "conditions" in edge:
                                temp_conditions = []
                                for condition in edge["conditions"]:
                                    temp_condition_data = condition.copy()
                                    for key in dict_keys:
                                        if key in condition:
                                            temp_condition_data[key] = re.sub(r"\b%s\b" % old_value, new_value,
                                                                              condition[key])
                                    temp_conditions.append(temp_condition_data)
                                edge_copy["conditions"] = temp_conditions
                            temp_edges_data.append(edge_copy)
                        temp_item_data["edges"] = temp_edges_data
                    elif fixture_key == self.CONTENTS:
                        changed_temp_item_data = []
                        for single_item_data in temp_item_data:
                            temp_single_item_data = single_item_data.copy()
                            if isinstance(single_item_data["content"], list):
                                temp_single_item_data["content"] = []
                                for temp_content in single_item_data["content"]:
                                    temp_content_copy = temp_content.copy()
                                    for key in dict_keys:
                                        if key in temp_content:
                                            if isinstance(temp_content[key], list):
                                                temp_content_list_copy_for_key = []
                                                for tc in temp_content[key]:
                                                    tc_temp = tc
                                                    if isinstance(tc, str):
                                                        tc_temp = re.sub(r"\b%s\b" % old_value, new_value,
                                                                                tc)
                                                    temp_content_list_copy_for_key.append(tc_temp)
                                            elif isinstance(temp_content[key], str):
                                                temp_content_copy[key] = re.sub(r"\b%s\b" % old_value, new_value,
                                                                                temp_content[key])
                                    temp_single_item_data["content"].append(temp_content)
                            elif isinstance(single_item_data["content"], str):
                                temp_single_item_data["content"] = re.sub(r"\b%s\b" % old_value, new_value,
                                                                          single_item_data["content"])
                            changed_temp_item_data.append(temp_single_item_data)
                    item["fields"]["data"] = json.dumps(temp_item_data)

    def _switch_regular_signals(self):
        from django.db.models import signals
        from system.signals import content_post_save, add_content_relations, \
            decorated_add_content_relations, decorated_content_post_save, reschedule_session, \
            decorated_reschedule_session
        logger.debug("Switching out regular signals")
        self.signals_not_switched_back = True
        signals.post_save.disconnect(add_content_relations, sender=Session)
        signals.post_save.connect(decorated_add_content_relations, sender=Session)
        signals.post_save.disconnect(content_post_save)
        signals.post_save.connect(decorated_content_post_save)
        signals.post_save.disconnect(reschedule_session, sender=Session)
        signals.post_save.connect(decorated_reschedule_session, sender=Session)

    def _switch_back_signals(self):
        from django.db.models import signals
        from system.signals import content_post_save, add_content_relations, \
            decorated_add_content_relations, decorated_content_post_save, reschedule_session, \
            decorated_reschedule_session
        logger.debug("Switching back regular signals")
        signals.post_save.disconnect(decorated_add_content_relations, sender=Session)
        signals.post_save.connect(add_content_relations, sender=Session)
        signals.post_save.disconnect(decorated_content_post_save)
        signals.post_save.connect(content_post_save)
        signals.post_save.disconnect(decorated_reschedule_session, sender=Session)
        signals.post_save.connect(reschedule_session, sender=Session)
        self.signals_not_switched_back = False

    def _handle_folders_fixtures(self):
        logger.debug("Updating folder fixtures")
        # We aren't selecting for update here, but we are assuming that no new folders will be uploaded...
        # TODO: Probably should protect/fix this
        latest_folder_pk = 1
        try:
            latest_folder = Folder.objects.latest("pk")
            latest_folder_pk = latest_folder.pk + 1
        except Folder.DoesNotExist:
            pass
        for folder in self.folders_fixtures:
            self.pk_mapping_dict[self.FOLDERS][folder.get("pk")] = latest_folder_pk
            folder["pk"] = latest_folder_pk
            latest_folder_pk += 1
        for folder in self.folders_fixtures:
            parent_folder_pk = folder.get("fields", {}).get("parent")
            if parent_folder_pk:
                folder["fields"]["parent"] = self.pk_mapping_dict[self.FOLDERS][parent_folder_pk]
        logger.debug("Saving folders to database")
        objects = serializers.deserialize(
            self.format,
            json.dumps(self.folders_fixtures, cls=DjangoJSONEncoder, ensure_ascii=False),
            handle_forward_references=True,
        )
        for obj in objects:
            obj.save()
            if obj.deferred_fields:
                self.objs_with_deferred_fields.append(obj)

    def _handle_file_fixtures(self):
        logger.debug("Updating file fixtures and saving to database")
        image_ctype = ContentType.objects.get_for_model(Image)
        file_ctype = ContentType.objects.get_for_model(File)
        image_ids = [image["pk"] for image in self.images_fixtures]

        # We aren't selecting for update here, but we are assuming that no new files will be uploaded...
        # TODO: Probably should protect/fix this
        latest_file_pk = 1
        try:
            latest_file = File.objects.latest("pk")
            latest_file_pk = latest_file.pk + 1
        except File.DoesNotExist:
            pass

        with open(self.file_path, "r") as fp:
            all_files = ijson.items(fp, "files.item")
            for file in all_files:
                file["fields"]["polymorphic_ctype"] = image_ctype.pk if file["pk"] in image_ids else file_ctype.pk
                file["fields"]["owner"] = None
                if file["fields"]["folder"]:
                    file["fields"]["folder"] = self.pk_mapping_dict[self.FOLDERS][file["fields"]["folder"]]
                self.pk_mapping_dict[self.FILES][file["pk"]] = latest_file_pk
                file["pk"] = latest_file_pk
                # TODO: this whole section can probably be fixed with a deserializer using ijson...
                objects = serializers.deserialize(
                    self.format,
                    json.dumps([file], cls=DjangoJSONEncoder, ensure_ascii=False),
                    handle_forward_references=True,
                )
                for obj in objects:
                    obj.save()
                    if obj.deferred_fields:
                        self.file_ids_with_deferred_fields.append(obj.pk)
                latest_file_pk += 1

        for image in self.images_fixtures:
            image["pk"] = self.pk_mapping_dict[self.FILES][image["pk"]]

    def _handle_deferred_fields_for_files(self):
        if self.file_ids_with_deferred_fields:
            image_ctype = ContentType.objects.get_for_model(Image)
            file_ctype = ContentType.objects.get_for_model(File)
            image_ids = [image["pk"] for image in self.images_fixtures]
            with open(self.file_path, "r") as fp:
                all_files = ijson.items(fp, "files.item")
                for file in all_files:
                    if self.pk_mapping_dict[self.FILES][file["pk"]] in self.file_ids_with_deferred_fields:
                        # this is a redo cuz we don't edit the json file..
                        file["fields"]["polymorphic_ctype"] = image_ctype.pk if file[
                                                                                    "pk"] in image_ids else file_ctype.pk
                        file["fields"]["owner"] = None
                        if file["fields"]["folder"]:
                            file["fields"]["folder"] = self.pk_mapping_dict[self.FOLDERS][file["fields"]["folder"]]
                        file["pk"] = self.pk_mapping_dict[self.FILES][file["pk"]]
                        objects = serializers.deserialize(
                            self.format,
                            json.dumps([file], cls=DjangoJSONEncoder, ensure_ascii=False),
                            handle_forward_references=True,
                        )
                        for obj in objects:
                            obj.save()
                            if obj.deferred_fields:
                                obj.save_deferred_fields()

    def _update_file_ids_in_contents(self):
        logger.debug("Updating file ids in contents")

        for content in self.contents_fixtures:
            temp_content_data = []
            # based on signals post content save (with no recursion iteration)
            for item in json.loads(content["fields"].get("data", json.dumps([]))):
                if item.get('content_type') == 'image' and item["content"]["file_id"]:
                    item["content"]["file_id"] = self.pk_mapping_dict[self.FILES][int(item["content"]["file_id"])]
                elif item.get('content_type') == 'toggle':
                    if 'img_content' in item and item["img_content"]["file_id"]:
                        item["img_content"]["file_id"] = self.pk_mapping_dict[self.FILES][int(item["img_content"]["file_id"])]
                temp_content_data.append(item)
            content["fields"]["data"] = json.dumps(temp_content_data)

    def _update_sessions_data_ref_id_and_url(self):
        """
        Because we disconnected the signals we assume that the title is the unique id of each object
        """
        logger.debug("Updating session data ref_id and ref_url after import")
        sessions_titles = set()
        for session in self.sessions_fixtures:
            sessions_titles.add(session.get("fields", {}).get("title"))
        sessions = Session.objects.select_for_update(no_key=True).filter(title__in=list(sessions_titles))
        db_connection = router.db_for_write(Program)
        with transaction.atomic(using=db_connection):
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
                            node['title'] = f'ERROR IN {node_type} IMPORT | OLD TITLE - {title}'
                            node['ref_id'] = f'ERROR IN {node_type} IMPORT | OLD REF_ID - {node["ref_id"]}'
                            node['ref_url'] = f'ERROR IN {node_type} IMPORT | OLD REF_URL - {node["ref_url"]}'

                data['nodes'] = nodes
                Session.objects.filter(id=new_session.id).update(data=data)

    def _trigger_content_post_save_for_each_content(self):
        logger.debug("Triggering content post save for each content")
        for content in self.contents_fixtures:
            title = content.get("fields", {}).get("title")
            content_type = content.get("fields", {}).get("content_type")
            try:
                ModelClass = Content
                if content_type == "page":
                    ModelClass = Page
                elif content_type == "email":
                    ModelClass = Email
                elif content_type == "sms":
                    ModelClass = SMS
                ModelClass.objects.get(title=title).save()
            except (Content.DoesNotExist, Page.DoesNotExist, Email.DoesNotExist, SMS.DoesNotExist):
                logger.exception(f"Couldn't get {title} - {content_type}")
                pass
