# -*- coding: utf-8 -*-
import os
import json
import warnings
from django.conf import settings
from django.core.management import call_command
from django.contrib.staticfiles.testing import LiveServerTestCase
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.auth.models import User
from sloth.test.selenium.browser import Browser


CACHE = dict(
    SEQUENCE=0,
    STEP=None,
    CONTINUE=None,
    RESUME=None,
    RECORD=None,
    HEADLESS=None,
    PAUSE=False
)


class TestStaticFilesHandler(StaticFilesHandler):
    def _middleware_chain(self, request):
        from django.http import HttpResponse
        return HttpResponse()


# StaticLiveServerTestCase
class SeleniumTestCase(LiveServerTestCase):
    static_handler = TestStaticFilesHandler

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_count = 0
        self.current_username = None
        warnings.filterwarnings('ignore')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser = Browser(cls.live_server_url)
        cls.browser.slowly = False
        for app_label in settings.INSTALLED_APPS:
            app_module = __import__(app_label)
            app_dir = os.path.dirname(app_module.__file__)
            fixture_path = os.path.join(app_dir, 'fixtures', 'test.json')
            if os.path.exists(fixture_path):
                call_command('loaddata', fixture_path)

    def create_superuser(self, username, password):
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, None, password)
        self.wait(1)

    def wait(self, seconds=1):
        self.browser.wait(seconds)

    def open(self, url):
        self.browser.open(url)

    def back(self, seconds=None):
        self.browser.back(seconds)

    def enter(self, name, value, submit=False, count=2):
        self.browser.enter(name, value, submit, count)

    def choose(self, name, value, count=2):
        self.browser.choose(name, value, count)

    def check(self, name=None):
        self.browser.check(name)

    def dont_see_error_message(self):
        self.browser.dont_see_error_message(self)

    def see(self, text, flag=True, count=2):
        self.browser.see(text, flag, count)

    def see_message(self, text, count=2):
        self.browser.see_message(text, count)

    def look_at_popup_window(self, count=2):
        self.browser.look_at_popup_window(count)

    def look_at(self, text, count=2):
        self.browser.look_at(text, count)

    def look_at_panel(self, text, count=2):
        self.browser.look_at_panel(text, count)

    def click_menu(self, *texts):
        self.browser.click_menu(*texts)

    def click_link(self, text):
        self.browser.click_link(text)

    def click_button(self, text):
        self.browser.click_button(text)

    def click_tab(self, text):
        self.browser.click_tab(text)

    def click_icon(self, name):
        self.browser.click_icon(name)

    def login(self, username, password):
        self.current_username = username
        self.open('/app/login/')
        self.enter('Login', username)
        self.enter('Senha', password)
        self.click_button('Acessar')
        self.wait()

    def logout(self):
        self.browser.logout()
        self.current_username = None

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.browser.close()
        cls.browser.service.stop()
        # len(self._resultForDoCleanups.errors)>0

    def dump(self, step):
        file_path = '/tmp/{}.test'.format(settings.PROJECT_NAME)
        dump_file_path = '/tmp/{}_{}.json'.format(settings.PROJECT_NAME, step)
        data = dict(step=step)
        open(file_path, 'w').write(json.dumps(data))
        output = open(dump_file_path, 'w')
        app_labels = []
        for app in settings.INSTALLED_APPS:
            app_label = app.split('.')[-1]
            if app_label not in 'auth':
                app_labels.append(app_label)
        User.objects.update(permission_mapping=None)
        call_command('dumpdata', *app_labels, format='json', indent=3, stdout=output, skip_checks=True, verbosity=0)
        output.close()

    def restore(self, step):
        dump_file_path = '/tmp/{}_{}.json'.format(settings.PROJECT_NAME, step)
        call_command('loaddata', dump_file_path)

    def execute_flow(self):
        flow = []

        for attr_name in dir(self):
            if not attr_name.startswith('_'):
                attr = getattr(self, attr_name)
                if hasattr(attr, '_sequence'):
                    flow.append(attr)

        if CACHE['STEP'] or CACHE['RESUME'] or CACHE['CONTINUE']:
            execute = False
        else:
            execute = True
        flow.sort(key=lambda x: x._sequence)
        for i, testcase in enumerate(flow):
            if execute:
                testcase()
            elif CACHE['RESUME']:
                if CACHE['RESUME'] == testcase._funcname:
                    self.restore(CACHE['RESUME'])
                    execute = True
            elif CACHE['STEP']:
                if CACHE['STEP'] == testcase._funcname:
                    if i > 0:
                        self.restore(flow[i - 1]._funcname)
                    testcase()
            elif CACHE['CONTINUE']:
                if CACHE['CONTINUE'] == testcase._funcname:
                    if i > 0:
                        self.restore(flow[i - 1]._funcname)
                    testcase()
                    execute = True

        if CACHE['PAUSE'] and not CACHE['HEADLESS']:
            input('Type enter to continue...')
