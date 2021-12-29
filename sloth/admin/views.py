# -*- coding: utf-8 -*-
import time

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string

from .. import views
from ..forms import FormMixin, LoginForm, PasswordForm
from ..utils.icons import bootstrap
from ..exceptions import JsonReadyResponseException, HtmlJsonReadyResponseException, ReadyResponseException
from . import gadgets


def view(func):
    def decorate(request, *args, **kwargs):
        try:
            #time.sleep(0.5)
            if views.is_authenticated(request):
                response = func(request, *args, **kwargs)
                response["X-Frame-Options"] = "SAMEORIGIN"
                return response
            else:
                return HttpResponseForbidden()
        except ReadyResponseException as e:
            return e.response
        except JsonReadyResponseException as e:
            return JsonResponse(e.data)
        except HtmlJsonReadyResponseException as e:
            messages = render_to_string('adm/messages.html', request=request)
            return HttpResponse(messages + e.html)
        except PermissionDenied:
            return HttpResponseForbidden()
        except BaseException as e:
            raise e

    return decorate


def icons(request):
    return render(request, ['adm/icons.html'], dict(bootstrap=bootstrap.ICONS))


def public(request):
    return render(request, ['adm/public.html'])


def login(request):
    form = LoginForm(request=request)
    if form.is_valid():
        form.process()
        return HttpResponseRedirect('/adm/')
    return render(request, ['adm/login.html'], dict(form=form, settings=settings))


def password(request):
    form = PasswordForm(request=request)
    if form.is_valid():
        form.process()
        return HttpResponseRedirect('..')
    return render(request, ['adm/default.html'], dict(form=form, settings=settings))


def logout(request):
    request.session.clear()
    request.session.save()
    auth.logout(request)
    return HttpResponseRedirect('/')


def index(request):
    if request.user.is_authenticated:
        gadgets.initilize()
        request.COOKIES.get('width')
        components = []
        for cls in gadgets.GADGETS.values():
            width = 100
            if hasattr(cls, 'Meta'):
                if hasattr(cls.Meta, 'can_view'):
                    names = cls.Meta.can_view
                    if not request.user.roles.filter(name__in=names).exists():
                        continue
                if hasattr(cls.Meta, 'width'):
                    width = cls.Meta.width
            components.append((width, cls(request).render()))
        return render(request, [settings.INDEX_TEMPLATE], dict(settings=settings, components=components))
    return HttpResponseRedirect('/adm/login/')


@view
def obj_view(request, app_label, model_name, x=None, y=None, z=None, w=None):
    context = dict(settings=settings)
    data = views.obj_view(request, app_label, model_name, x=x, y=y, z=z, w=w)
    if isinstance(data, FormMixin):
        context.update(form=data)
        if data.message:
            if data.message.get('reload'):
                return HttpResponse('.')
            return HttpResponse('..')
    else:
        context.update(data=data)
    return render(request, ['adm/default.html'], context)
