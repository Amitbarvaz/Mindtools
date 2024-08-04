from django.contrib import messages
from django.contrib.admin.helpers import AdminForm
from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _


def direct_message_action_for_admin(modeladmin, request, user, form_url, FormClass, title,
                                    success_message, failure_message, send_action_value, check_phone=False, ):
    if not modeladmin.has_change_permission(request, user):
        raise PermissionDenied
    if user is None:
        raise Http404(
            _("%(name)s object with primary key %(key)r does not exist.")
            % {
                "name": modeladmin.opts.verbose_name,
                "key": escape(user.id),
            }
        )

    if check_phone and not user.phone and not user.secondary_phone:
        messages.error(request,
                       _("%(user)s does not have a phone number.")
                       % {
                           "user": user.get_username(),
                       }
                       )
        return HttpResponseRedirect(
            reverse(
                "%s:%s_%s_change"
                % (
                    modeladmin.admin_site.name,
                    user._meta.app_label,
                    user._meta.model_name,
                ),
                args=(user.pk,),
            )
        )

    if request.method == "POST":
        form = FormClass(user, request.POST)
        if form.is_valid():
            successful_result = form.save()
            if successful_result:
                messages.success(request, success_message)
            else:
                messages.error(request, failure_message)
            return HttpResponseRedirect(
                reverse(
                    "%s:%s_%s_change"
                    % (
                        modeladmin.admin_site.name,
                        user._meta.app_label,
                        user._meta.model_name,
                    ),
                    args=(user.pk,),
                )
            )
    else:
        form = FormClass(user)

    fieldsets = [(None, {"fields": list(form.base_fields)})]
    admin_form = AdminForm(form, fieldsets, {})

    context = {
        "title": title,
        "adminform": admin_form,
        "form_url": form_url,
        "form": form,
        "is_popup": (IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
        "is_popup_var": IS_POPUP_VAR,
        "add": True,
        "change": False,
        "has_delete_permission": False,
        "has_change_permission": True,
        "has_absolute_url": False,
        "opts": modeladmin.opts,
        "original": user,
        "save_as": False,
        "show_save": True,
        "send_action_value": send_action_value,
        **modeladmin.admin_site.each_context(request),
    }

    request.current_app = modeladmin.admin_site.name

    return TemplateResponse(
        request,
        modeladmin.direct_email_or_sms_template,
        context,
    )
