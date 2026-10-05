from django.utils import translation


def ui(request):
    lang = translation.get_language() or "en"
    return {"is_rtl": lang.startswith("ar"), "ui_lang": lang[:2]}
