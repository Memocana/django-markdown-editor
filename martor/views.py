import json
from django.http import HttpResponse
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q

from .api import imgur_uploader
from .settings import MARTOR_MARKDOWNIFY_FUNCTION
from .utils import LazyEncoder

from django import template
from django.conf import settings
import markdown
import bleach
import re
from django.utils.safestring import mark_safe

register = template.Library()
User = get_user_model()

def markdownify(text):

    # Get the settings or set defaults if not set
    whitelist_tags = getattr(settings, 'MARKDOWNIFY_WHITELIST_TAGS', bleach.sanitizer.ALLOWED_TAGS)
    whitelist_attrs = getattr(settings, 'MARKDOWNIFY_WHITELIST_ATTRS', bleach.sanitizer.ALLOWED_ATTRIBUTES)
    whitelist_styles = getattr(settings, 'MARKDOWNIFY_WHITELIST_STYLES', bleach.sanitizer.ALLOWED_STYLES)
    whitelist_protocols = getattr(settings, 'MARKDOWNIFY_WHITELIST_PROTOCOLS', bleach.sanitizer.ALLOWED_PROTOCOLS)
    strip = getattr(settings, 'MARKDOWNIFY_STRIP', True)
    extensions = getattr(settings, 'MARKDOWNIFY_MARKDOWN_EXTENSIONS', [])

    # Convert markdown to html
    print(mentions(text))
    text = mentions(text)
    html = markdown.markdown(text, extensions=extensions)

    # Sanitize html if wanted
    if getattr(settings, 'MARKDOWNIFY_BLEACH', True):
        html = bleach.clean(html,
                            tags=whitelist_tags,
                            attributes=whitelist_attrs,
                            styles=whitelist_styles,
                            protocols=whitelist_protocols,
                            strip=strip,)

        html = bleach.linkify(html)

    return mark_safe(html)

def mentions(text):
    url = getattr(settings, 'MARTOR_MARKDOWN_BASE_MENTION_URL', "dev.portfolio.robotuz.biz/u/")
    text = re.sub(r'@\[(.*)\]', r'<a target="_blank" href="'+url+r'\1">\1</a>', text.rstrip())
    return text

def markdownfy_view(request):
    if request.method == 'POST':
        return HttpResponse(markdownify(request.POST['content']))
    return HttpResponse(_('Invalid request!'))


@login_required
def markdown_imgur_uploader(request):
    """
    Makdown image upload for uploading to imgur.com
    and represent as json to markdown editor.
    """
    if request.method == 'POST' and request.is_ajax():
        if 'markdown-image-upload' in request.FILES:
            image = request.FILES['markdown-image-upload']
            data = imgur_uploader(image)
            return HttpResponse(data, content_type='application/json')
        return HttpResponse(_('Invalid request!'))
    return HttpResponse(_('Invalid request!'))


@login_required
def markdown_search_user(request):
    """
    Json usernames of the users registered & actived.

    url(method=get):
        /martor/search-user/?username={username}

    Response:
        error:
            - `status` is status code (204)
            - `error` is error message.
        success:
            - `status` is status code (204)
            - `data` is list dict of usernames.
                { 'status': 200,
                  'data': [
                    {'usernane': 'john'},
                    {'usernane': 'albert'}]
                }
    """
    data = {}
    username = request.GET.get('username')
    print(username)
    if username is not None \
            and username != '' \
            and ' ' not in username:
        users = User.objects.filter(
            Q(username__icontains=username)
        ).filter(is_active=True)
        print(users)
        if users.exists():
            data.update({
                'status': 200,
                'data': [{'username': u.username} for u in users]
            })
            return HttpResponse(
                json.dumps(data, cls=LazyEncoder),
                content_type='application/json')
        data.update({
            'status': 204,
            'error': _('No users registered as `%(username)s` '
                       'or user is unactived.') % {'username': username}
        })
    else:
        data.update({
            'status': 204,
            'error': _('Validation Failed for field `username`')
        })
    return HttpResponse(
        json.dumps(data, cls=LazyEncoder),
        content_type='application/json')
