import json
import logging
import sys
import time
import urlparse

from glanceclient import client as gclient
from keystoneclient.v2_0 import client as ksclient
from muranoclient import client as mclient
from selenium.common import exceptions as exc
from selenium import webdriver
import selenium.webdriver.common.by as by
from selenium.webdriver.support.ui import WebDriverWait
import testtools

import config.config as cfg
from muranodashboard.tests.functional import consts
from muranodashboard.tests.functional import utils

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

if sys.version_info >= (2, 7):
    class BaseDeps(testtools.TestCase):
        pass
else:
    # Define asserts for python26
    import unittest2

    class BaseDeps(testtools.TestCase,
                   unittest2.TestCase):
        pass


class OrderedMethodMixin(object):
    __metaclass__ = utils.OrderedMethodMetaclass


class UITestCase(OrderedMethodMixin, BaseDeps):
    @classmethod
    def setUpClass(cls):
        cls.keystone_client = ksclient.Client(username=cfg.common.user,
                                              password=cfg.common.password,
                                              tenant_name=cfg.common.tenant,
                                              auth_url=cfg.common.keystone_url)
        cls.murano_client = mclient.Client(
            '1', endpoint=cfg.common.murano_url,
            token=cls.keystone_client.auth_token)
        cls.url_prefix = urlparse.urlparse(cfg.common.horizon_url).path or ''
        if cls.url_prefix.endswith('/'):
            cls.url_prefix = cls.url_prefix[:-1]

    def setUp(self):
        super(UITestCase, self).setUp()

        self.driver = webdriver.Firefox()
        self.driver.maximize_window()
        self.driver.get(cfg.common.horizon_url + '/')
        self.driver.implicitly_wait(30)
        self.log_in()

    def tearDown(self):
        super(UITestCase, self).tearDown()
        self.driver.quit()

        for env in self.murano_client.environments.list():
            self.murano_client.environments.delete(env.id)

    def log_in(self):
        self.fill_field(by.By.ID, 'id_username', cfg.common.user)
        self.fill_field(by.By.ID, 'id_password', cfg.common.password)
        self.driver.find_element_by_xpath("//button[@type='submit']").click()
        self.driver.find_element_by_xpath(consts.Murano).click()

    def fill_field(self, by_find, field, value):
        self.driver.find_element(by=by_find, value=field).clear()
        self.driver.find_element(by=by_find, value=field).send_keys(value)

    def get_element_id(self, el_name):
        path = self.driver.find_element_by_xpath(
            ".//*[@data-display='{0}']".format(el_name)).get_attribute("id")
        return path.split('__')[-1]

    def select_and_click_action_for_app(self, action, app):
        self.driver.find_element_by_xpath(
            "//*[@href='{0}/murano/catalog/{1}/{2}']".format(self.url_prefix,
                                                             action,
                                                             app)).click()

    def go_to_submenu(self, link):
        self.driver.find_element_by_partial_link_text(
            '{0}'.format(link)).click()
        time.sleep(2)

    def check_panel_is_present(self, panel_name):
        self.assertIn(panel_name,
                      self.driver.find_element_by_xpath(
                          ".//*[@class='page-header']").text)

    def navigate_to(self, menu):
        self.driver.find_element_by_xpath(getattr(consts, menu)).click()

    def select_from_list(self, list_name, value):
        self.driver.find_element_by_xpath(
            "//select[@name='{0}']/option[text()='{1}']".
            format(list_name, value)).click()

    def check_element_on_page(self, method, value):
        try:
            self.driver.find_element(method, value)
        except (exc.NoSuchElementException, exc.ElementNotVisibleException):
            self.fail("Element {0} is not preset on the page".format(value))

    def check_element_not_on_page(self, method, value):
        self.driver.implicitly_wait(3)
        present = True
        try:
            self.driver.find_element(method, value)
        except (exc.NoSuchElementException, exc.ElementNotVisibleException):
            present = False
        self.assertFalse(present, "Element {0} is preset on the page"
                                  " while it should't".format(value))
        self.driver.implicitly_wait(30)

    def create_environment(self, env_name):
        self.driver.find_element_by_id(
            'murano__action_CreateEnvironment').click()
        self.fill_field(by.By.ID, 'id_name', env_name)
        self.driver.find_element_by_xpath(consts.InputSubmit).click()
        WebDriverWait(self.driver, 10).until(lambda s: s.find_element(
            by.By.LINK_TEXT, 'Add Component').is_displayed())

    def check_alert_message(self, driver):
        el = driver.find_element_by_css_selector('div.alert')
        return not el.is_displayed()


class PackageBase(UITestCase):
    @classmethod
    def setUpClass(cls):
        super(PackageBase, cls).setUpClass()
        cls.mockapp_id = utils.upload_app_package(
            cls.murano_client,
            "MockApp",
            {"categories": ["Web"], "tags": ["tag"]})
        cls.postgre_id = utils.upload_app_package(
            cls.murano_client,
            "PostgreSQL",
            {"categories": ["Databases"], "tags": ["tag"]})

    @classmethod
    def tearDownClass(cls):
        super(PackageBase, cls).tearDownClass()
        cls.murano_client.packages.delete(cls.mockapp_id)
        cls.murano_client.packages.delete(cls.postgre_id)


class ImageTestCase(PackageBase):
    @classmethod
    def setUpClass(cls):
        super(ImageTestCase, cls).setUpClass()
        glance_endpoint = cls.keystone_client.service_catalog.url_for(
            service_type='image', endpoint_type='publicURL')
        cls.glance = gclient.Client('1', endpoint=glance_endpoint,
                                    token=cls.keystone_client.auth_token)
        cls.image = cls.upload_image()

    @classmethod
    def tearDownClass(cls):
        super(ImageTestCase, cls).tearDownClass()
        cls.glance.images.delete(cls.image.id)

    @classmethod
    def upload_image(cls):
        try:
            property = {'murano_image_info': json.dumps({'title': 'New Image',
                                                         'type': 'linux'})}
            image = cls.glance.images.create(name='TestImage',
                                             disk_format='qcow2',
                                             size=0,
                                             is_public=True,
                                             properties=property)
        except Exception as e:
            log.exception("Unable to create or update image in Glance")
            raise e
        return image

    def select_and_click_element(self, element):
        self.driver.find_element_by_xpath(
            ".//*[@value = '{0}']".format(element)).click()

    def repair_image(self):
        self.driver.find_element_by_id(
            'marked_images__action_mark_image').click()
        self.select_from_list('image', self.image.name)
        self.fill_field(by.By.ID, 'id_title', 'New Image')
        self.select_from_list('type', 'Generic Linux')
        self.select_and_click_element('Mark')


class EnvironmentTestCase(UITestCase):
    def delete_environment(self, env_name):
        self.select_action_for_environment(env_name, 'delete')
        self.driver.find_element_by_xpath(consts.ConfirmDeletion).click()
        WebDriverWait(self.driver, 10).until(self.check_alert_message)

    def edit_environment(self, old_name, new_name):
        self.select_action_for_environment(old_name, 'edit')
        self.fill_field(by.By.ID, 'id_name', new_name)
        self.driver.find_element_by_xpath(consts.InputSubmit).click()

    def select_action_for_environment(self, env_name, action):
        element_id = self.get_element_id(env_name)
        more_button = consts.More.format(element_id)
        self.driver.find_element_by_xpath(more_button).click()
        btn_id = "murano__row_{0}__action_{1}".format(element_id, action)
        WebDriverWait(self.driver, 10).until(
            lambda s: s.find_element_by_id(btn_id).is_displayed)
        self.driver.find_element_by_id(btn_id).click()


class FieldsTestCase(PackageBase):
    def check_error_message_is_present(self, error_message):
        self.driver.find_element_by_xpath(consts.ButtonSubmit).click()
        self.driver.find_element_by_xpath(
            '//div[@class="alert-message"]'
            '[contains(text(), "{0}")]'.format(error_message))

    def check_error_message_is_absent(self, error_message):
        self.driver.find_element_by_xpath(consts.ButtonSubmit).click()

        self.driver.implicitly_wait(2)
        try:
            self.driver.find_element_by_xpath(
                '//div[@class="alert-message"]'
                '[contains(text(), "{0}")]'.format(error_message))
        except (exc.NoSuchElementException, exc.ElementNotVisibleException):
            log.info("Message {0} is not"
                     " present on the page".format(error_message))

        self.driver.implicitly_wait(30)


class ApplicationTestCase(ImageTestCase):
    def delete_component(self, component_name):
        component_id = self.get_element_id(component_name)
        self.driver.find_element_by_id(
            'services__row_{0}__action_delete'.format(component_id)).click()
        self.driver.find_element_by_link_text('Delete Component').click()
        WebDriverWait(self.driver, 10).until(self.check_alert_message)

    def select_action_for_package(self, package, action):
        package_id = self.get_element_id(package)
        if action == 'more':
            self.driver.find_element_by_xpath(
                ".//*[@id='packages__row__{0}']/td[6]/div/a[2]".
                format(package_id)).click()
            WebDriverWait(self.driver, 10).until(lambda s: s.find_element(
                by.By.XPATH,
                ".//*[@id='packages__row_{0}__action_download_package']".
                format(package_id)).is_displayed())
        else:
            self.driver.find_element_by_xpath(
                ".//*[@id='packages__row_{0}__action_{1}']".
                format(package_id, action)).click()

    def check_package_parameter(self, package, column, value):
        package_id = self.get_element_id(package)

        result = self.driver.find_element_by_xpath(
            ".//*[@id='packages__row__{0}']/td[{1}]".
            format(package_id, column)).text
        if result == value:
            return True
        else:
            return False

    def modify_package(self, param, value):
        self.fill_field(by.By.ID, 'id_{0}'.format(param), value)
        self.driver.find_element_by_xpath(consts.InputSubmit).click()
        self.driver.refresh()
