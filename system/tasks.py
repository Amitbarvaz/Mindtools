from __future__ import unicode_literals

import time

from django.utils.translation import gettext_lazy as _

from django.contrib.auth import get_user_model
from django.utils import timezone
from huey.contrib.djhuey import db_task
from system.engine import Engine
from tasker.models import Task

import logging

logger = logging.getLogger('debug')

def _rewrite_node_if_needed(engine, original_session_id, original_node_id):
    engine.refresh_user()
    current_user_session_id = engine.user.data.get('session')
    current_user_node_id = engine.user.data.get('node')

    if original_session_id == current_user_session_id and \
            original_node_id is not None and original_node_id > 0 and \
            current_user_node_id != original_node_id and \
            engine.is_node_chaptered_page(original_node_id):
        logger.debug('Rewrite node_id to %s for chaptered page in session %s for user %s',
                     original_node_id,
                     original_session_id,
                     engine.user.id)
        engine.user.data['node'] = original_node_id
        engine.user.save()
        return original_node_id
    return current_user_node_id

@db_task()
def transition(session_id, node_id, user_id, stack=None):
    '''A task to schedule an Engine transition'''

    logger.debug('transition called with session_id=%s, node_id=%s, user_id=%s, stack=%s',
                session_id,
                node_id,
                user_id,
                stack)
    context = {
        'session': session_id,
        'node': node_id,
        'stack': stack or []
    }

    engine = Engine(user_id=user_id, context=context)

    if not engine.user.is_active:
        return _('Inactive user, no action taken')

    user_session_id = engine.user.data.get('session')
    user_node_id = engine.user.data.get('node')

    node = engine.transition(node_id)
    new_node_id = _rewrite_node_if_needed(engine, user_session_id, user_node_id)

    message = _('%(session)s transitioned to node %(node)s') % {
        'session': engine.session.title,
        'node': getattr(node, 'name', node_id) if new_node_id == node_id else new_node_id
    }

    return message


@db_task()
def init_session(session_id, user_id, push=False):
    '''Initialize a given session from start and traverse on behalf of user'''

    logger.debug('init_session called with session_id=%s, user_id=%s, push=%s',
                session_id,
                user_id,
                push)
    context = {
        'session': session_id,
        'node': 0,
    }

    if not push:
        context['stack'] = []

    engine = Engine(user_id=user_id, context=context, push=push)
    user_session_id = engine.user.data.get('session')
    user_node_id = engine.user.data.get('node')
    original_session = engine.session

    if not engine.user.is_active:
        return _('Inactive user, no action taken')

    engine.run()
    _rewrite_node_if_needed(engine, user_session_id, user_node_id)

    engine.refresh_user()
    if engine.session.trigger_login:
        engine.user.send_login_link()
        message = _('Session initialized and login e-mail sent')
    else:
        message = _('Session initialized')

    if engine.user.is_active and original_session.scheduled and original_session.end_time_delta > 0:
        useraccess = engine.user.get_first_program_user_access(original_session.program)
        if original_session.get_end_time(useraccess.start_time, useraccess.time_factor) > \
                original_session.get_next_time(useraccess.start_time, useraccess.time_factor):

            next_time = original_session.get_next_time(useraccess.start_time, useraccess.time_factor)
            Task.objects.create_task(
                sender=original_session,
                domain='init',
                time=next_time,
                task=init_session,
                args=(session_id, user_id),
                action=_('Initialize session recurrent'),
                subject=engine.user
            )

    return message
