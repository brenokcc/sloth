# -*- coding: utf-8 -*-

import time
import datetime
import traceback
from selenium import webdriver
from django.conf import settings
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import WebDriverException


class Browser(webdriver.Firefox):
    def __init__(self, server_url, options=None, verbose=True, slowly=False, maximize=True, headless=False):

        if not options:
            options = Options()
        if maximize:
            options.add_argument("--start-maximized")
        else:
            options.add_argument("--window-size=720x800")
        if headless:
            options.add_argument("--headless")

        super().__init__(options=options)

        self.verbose = verbose
        self.slowly = slowly
        self.watched = False
        self.server_url = server_url

        if maximize:
            self.maximize_window()
        else:
            self.set_window_position(700, 0)
            self.set_window_size(720, 800)
        self.switch_to.window(self.current_window_handle)

    def slow_down(self):
        self.slowly = True

    def speed_up(self):
        self.slowly = False

    def wait(self, seconds=1):
        time.sleep(seconds)

    def watch(self, e):
        if self.watched:
            raise e
        else:
            traceback.print_exc()
            self.watched = True
            self.save_screenshot('/tmp/test.png')

    def print(self, message):
        if self.verbose:
            print(message)

    def execute_script(self, script, *args):
        super().execute_script(script, *args)
        if self.slowly:
            self.wait(3)

    def open(self, url):
        self.get("{}{}".format(self.server_url, url))

    def pdb(self):
        breakpoint()

    def back(self, seconds=None):
        if seconds:
            self.wait(seconds)
        if not self.current_url or not self.current_url.endswith('/app/'):
            self.open('/app/')

    def enter(self, name, value, submit=False, count=2):

        if callable(value):
            value = value()
        if type(value) == datetime.date:
            value = value.strftime('%d/%m/%Y')
        if value:
            self.print('{} "{}" for "{}"'.format('Entering', value, name))
        try:
            if submit:
                self.execute_script("enter('{}', '{}', 1)".format(name, value))
            else:
                self.execute_script("enter('{}', '{}')".format(name, value))
                elements = self.find_elements_by_name('hidden-upload-value')
                for element in elements:
                    element_id, file_path = element.get_property('value').split(':')
                    if file_path.startswith('/static'):
                        file_path = '{}/{}/{}'.format(settings.BASE_DIR, settings.PROJECT_NAME, file_path)
                    self.find_element_by_id(element_id).send_keys(file_path)
        except WebDriverException as e:
            if count:
                self.wait()
                self.enter(name, value, submit, count - 1)
            else:
                self.watch(e)
        if self.slowly:
            self.wait(2)

    def choose(self, name, value, count=2):
        self.print('{} "{}" for "{}"'.format('Choosing', value, name))
        try:
            headless = 'false'
            self.execute_script("choose('{}', '{}', {})".format(name, value, headless))
            self.wait(2)
        except WebDriverException as e:
            if count:
                self.wait()
                self.choose(name, value, count - 1)
            else:
                self.watch(e)
        if self.slowly:
            self.wait(2)

    def dont_see_error_message(self, testcase=None):
        elements = self.find_elements_by_class_name('alert-danger')
        if elements:
            messages = [element.text for element in elements]
            if True:
                input('Type enter to continue...')
            elif testcase:
                exception_message = 'The following messages were found on the page: {}'.format(';'.join(messages))
                raise testcase.failureException(exception_message)

    def see(self, text, flag=True, count=2):
        if flag:
            self.print('See "{}"'.format(text))
            try:
                assert text in self.find_element_by_tag_name('body').text
            except WebDriverException as e:
                if count:
                    self.wait()
                    self.see(text, flag, count - 1)
                else:
                    self.watch(e)
            if self.slowly:
                self.wait(2)
        else:
            self.print('Can\'t see "{}"'.format(text))
            assert text not in self.find_element_by_tag_name('body').text

    def see_message(self, text, count=2):
        self.print('See message {}'.format(text))
        try:
            self.execute_script("seeMessage('{}')".format(text))
        except WebDriverException as e:
            if count:
                self.wait()
                self.see_message(count - 1)
            else:
                self.watch(e)
        if self.slowly:
            self.wait(2)

    def look_at_popup_window(self, count=2):
        self.print('Looking at popup window')
        try:
            self.execute_script("lookAtPopupWindow()")
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_at_popup_window(count - 1)
            else:
                self.watch(e)
        if self.slowly:
            self.wait(2)

    def look_at(self, text, count=2):
        self.print('Loking at "{}"'.format(text))
        try:
            self.execute_script("lookAt('{}')".format(text))
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_at(text, count - 1)
            else:
                self.watch(e)
        if self.slowly:
            self.wait(2)

    def look_at_panel(self, text, count=2):
        self.print('Looking at panel "{}"'.format(text))
        try:
            self.execute_script("lookAtPanel('{}')".format(text))
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_at_panel(text, count - 1)
            else:
                self.watch(e)
        if self.slowly:
            self.wait(2)

    def check(self, text=None):
        self.print('Checking "{}"'.format(text))
        try:
            if text:
                self.execute_script("check('{}')".format(text))
            else:
                self.execute_script("check()")
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def click_menu(self, *texts):
        self.print('Clicking menu "{}"'.format('->'.join(texts)))
        for text in texts:
            try:
                self.execute_script("clickMenu('{}')".format(text.strip()))
            except WebDriverException as e:
                self.watch(e)
        self.wait()

    def click_link(self, text):
        self.print('Clicking link "{}"'.format(text))
        try:
            self.execute_script("clickLink('{}')".format(text))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def click_button(self, text):
        self.print('Clicking button "{}"'.format(text))
        try:
            self.execute_script("clickButton('{}')".format(text))
        except WebDriverException as e:
            self.watch(e)
        self.wait()
        self.dont_see_error_message()

    def click_tab(self, text):
        self.print('Clicking tab "{}"'.format(text))
        try:
            self.execute_script("clickTab('{}')".format(text))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def click_icon(self, name):
        self.print('Clicking icon "{}"'.format(name))
        try:
            self.execute_script("clickIcon('{}')".format(name))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def logout(self):
        self.print('Logging out')
        self.click_link('settings')
        self.wait()
        self.click_link('Sair')
        self.wait()

    def close(self, seconds=0):
        self.wait(seconds)
        super().close()
