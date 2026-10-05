from django import template

from apps.core.permissions import user_can

register = template.Library()


@register.simple_tag(takes_context=True)
def can(context, module, action="view"):
    return user_can(context["request"].user, module, action)


@register.simple_tag
def display_name(user, lang="en"):
    return user.display_name(lang)
