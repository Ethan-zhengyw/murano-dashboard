import os
import sys
sys.path.append(os.getcwd())

import selenium.webdriver.common.by as by
from selenium.webdriver.support.ui import WebDriverWait
import testtools

from base import UITestCase


class UISanityTests(UITestCase):

    def test_001_create_delete_environment(self):
        """Test check ability to create and delete environment

        Scenario:
            1. Create environment
            2. Navigate to this environment
            3. Go back to environment list and delete created environment
        """
        self.go_to_submenu('Environments')
        self.create_environment('test_create_del_env')
        self.driver.find_element_by_link_text('test_create_del_env').click()

        self.delete_environment('test_create_del_env')
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'test_create_del_env'))

    def test_002_edit_environment(self):
        """Test check ability to change environment name

        Scenario:
            1. Create environment
            2. Change environment's name
            3. Check that there is renamed environment is in environment list
        """
        self.go_to_submenu('Environments')
        self.create_environment('test_edit_env')
        self.driver.find_element_by_link_text('test_edit_env')

        self.edit_environment(old_name='test_edit_env', new_name='edited_env')
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'edited_env'))
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'test_edit_env'))

    def test_003_rename_image(self):
        """Test check ability to mark murano image

        Scenario:
            1. Navigate to Images page
            2. Click on button "Mark Image"
            3. Fill the form and submit it
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.driver.find_element_by_id(
            'marked_images__action_mark_image').click()

        self.select_from_list('image', 'TestImageForDeletion')
        self.fill_field(by.By.ID, 'id_title', 'New Image')
        self.select_from_list('type', ' Windows Server 2012')

        self.select_and_click_element('Mark')

    def test_004_delete_image(self):
        """Test check ability to delete image

        Scenario:
            1. Navigate to Images page
            2. Create test image
            3. Select created image and click on "Delete Metadata"
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.driver.find_element_by_id(
            'marked_images__action_mark_image').click()

        self.select_from_list('image', 'TestImageForDeletion')
        self.fill_field(by.By.ID, 'id_title', 'Image for deletion')
        self.select_from_list('type', ' Windows Server 2012')

        self.select_and_click_element('Mark')

        element_id = self.get_element_id('TestImageForDeletion')
        self.driver.find_element_by_id(
            "marked_images__row_%s__action_delete" % element_id).click()
        self.confirm_deletion()
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'TestImageForDeletion'))

    def test_005_check_image_info(self):
        """Test check ability to view image details

        Scenario:
            1. Navigate to Images page
            2. Create test image
            3. Click on the name of selected image, check image info
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.driver.find_element_by_id(
            'marked_images__action_mark_image').click()

        self.select_from_list('image', 'TestImageForDeletion')
        self.fill_field(by.By.ID, 'id_title', 'TestImage')
        self.select_from_list('type', ' Windows Server 2012')

        self.select_and_click_element('Mark')

        self.driver.find_element_by_link_text('TestImageForDeletion').click()
        self.assertIn('{"type": "windows.2012", "title": "TestImage"}',
                      self.driver.page_source)

    def test_006_create_and_delete_linux_telnet(self):
        """Test check ability to create and delete Linux Telnet service

        Scenario:
            1. Navigate to 'Application Catalog'
            2. Click on 'Quick Deploy' for Telnet application
            3. Create Linux Telnet app by filling the creation form
            4. Delete Linux Telnet app from environment
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        telnet_id = self.get_element_id('Telnet')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')

        self.create_linux_telnet('linuxtelnet', telnet_id)

        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'linuxtelnet'))
        self.delete_component('linuxtelnet')
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'linuxtelnet'))

    def test_007_create_and_delete_linux_apache(self):
        """Test check ability to create and delete Linux Apache service

        Scenario:
            1. Navigate to 'Application Catalog'
            2. Click on 'Quick Deploy' for Apache application
            3. Create Linux Apache app by filling the creation form
            4. Delete Linux Apache app from environment
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        apache_id = self.get_element_id('Apache HTTP Server')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')

        self.create_linux_apache('linuxapache', apache_id)

        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'linuxapache'))
        self.delete_component('linuxapache')
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'linuxapache'))

    def test_008_create_and_delete_ad_service(self):
        """Test check ability to create and delete Active Directory service

        Scenario:
            1. Navigate to 'Application Catalog'
            2. Click on 'Quick Deploy' for Active Directory application
            3. Create Active Directory app by filling the creation form
            4. Delete Active Directory app from environment
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        ad_id = self.get_element_id('Active Directory')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', ad_id)
        self.create_ad_service('muranotest.domain')

        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'muranotest.domain'))

        self.delete_component('muranotest.domain')
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'muranotest.domain'))

    def test_009_create_and_delete_tomcat_service(self):
        """Test check ability to create and delete Tomcat service

        Scenario:
            1. Navigate to 'Application Catalog'
            2. Click on 'Quick Deploy' for Tomcat application
            3. Firstly, create PostgreSQL app by filling the creation form
            4. Create Tomcat app, in case of database select created
            early PostgreSQL
            5. Delete Tomcat app from environment
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        tomcat_id = self.get_element_id('Apache Tomcat')
        postgre_id = self.get_element_id('PostgreSQL')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Environments')
        self.create_environment('test')
        env_id = self.get_element_id('test')
        self.env_to_components_list('test')

        self.driver.find_element_by_link_text('Add Component').click()
        self.select_and_click_action_for_app('add/{0}'.format(env_id),
                                             postgre_id)
        self.create_postgreSQL_service('PostgreSQL')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'PostgreSQL'))

        self.driver.find_element_by_link_text('Add Component').click()
        self.select_and_click_action_for_app('add/{0}'.format(env_id),
                                             tomcat_id)

        self.create_tomcat_service('tomcat-serv', 'PostgreSQL')
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'tomcat-serv'))
        self.delete_component('tomcat-serv')
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'tomcat-serv'))

    def test_010_create_and_delete_postgreSQL_service(self):
        """Test check ability to create and delete PostgreSQL service

        Scenario:
            1. Navigate to 'Application Catalog'
            2. Click on 'Quick Deploy' for PostgreSQL application
            3. Create PostgreSQL app by filling the creation form
            4. Delete PostgreSQL app from environment
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        postgresql_id = self.get_element_id('PostgreSQL')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', postgresql_id)
        self.create_postgreSQL_service('PostgreSQL')
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'PostgreSQL'))

        self.delete_component('PostgreSQL')
        self.assertFalse(self.check_element_on_page(by.By.LINK_TEXT,
                                                    'PostgreSQL'))

    @testtools.skip("https://bugs.launchpad.net/murano/+bug/1321690")
    def test_011_check_regex_expression_for_ad_name(self):
        """Test check that validation of domain name field work and appropriate
        error message is appeared after entering incorrect domain name

        Scenario:
            1. Navigate to Environments page
            2. Create environment and start to create AD service
            3. Set "a" as a domain name and verify error message
            4. Set "aa" as a domain name and check that error message
            didn't appear
            5. Set "@ct!v3" as a domain name and verify error message
            6. Set "active.com" as a domain name and check that error message
            didn't appear
            7. Set "domain" as a domain name and verify error message
            8. Set "domain.com" as a domain name and check that error message
            didn't appear
            9. Set "morethan15symbols.beforedot" as a domain name and
            verify error message
            10. Set "lessthan15.beforedot" as a domain name and check that
            error message didn't appear
            11. Set ".domain.local" as a domain name and
            verify error message
            12. Set "domain.local" as a domain name and check that
            error message didn't appear
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        ad_id = self.get_element_id('Active Directory')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', ad_id)

        self.fill_field(by.By.ID, field='id_0-name', value='a')
        self.assertTrue(self.check_that_error_message_is_correct(
            'Ensure this value has at least 2 characters (it has 1).', 1))

        self.fill_field(by.By.ID, field='id_0-name', value='aa')
        self.assertFalse(self.check_that_error_message_is_correct(
            'Ensure this value has at least 2 characters (it has 1).', 1))

        self.fill_field(by.By.ID, field='id_0-name', value='@ct!v3')
        self.assertTrue(self.check_that_error_message_is_correct(
            'Only letters, numbers and dashes in the middle are allowed.', 1))

        self.fill_field(by.By.ID, field='id_0-name', value='active.com')
        self.assertFalse(self.check_that_error_message_is_correct(
            'Only letters, numbers and dashes in the middle are allowed.', 1))

        self.fill_field(by.By.ID, field='id_0-name', value='domain')
        self.assertTrue(self.check_that_error_message_is_correct(
            'Single-level domain is not appropriate.', 1))

        self.fill_field(by.By.ID, field='id_0-name', value='domain.com')
        self.assertFalse(self.check_that_error_message_is_correct(
            'Single-level domain is not appropriate.', 1))

        self.fill_field(by.By.ID, field='id_0-name',
                        value='morethan15symbols.beforedot')
        self.assertTrue(self.check_that_error_message_is_correct(
            'NetBIOS name cannot be shorter than'
            ' 1 symbol and longer than 15 symbols.', 1))

        self.fill_field(by.By.ID, field='id_0-name',
                        value='lessthan15.beforedot')
        self.assertFalse(self.check_that_error_message_is_correct(
            'NetBIOS name cannot be shorter than'
            ' 1 symbol and longer than 15 symbols.', 1))

        self.fill_field(by.By.ID, field='id_0-name', value='.domain.local')
        self.assertTrue(self.check_that_error_message_is_correct(
            'Period characters are allowed only when '
            'they are used to delimit the components of domain style names',
            1))

        self.fill_field(by.By.ID, field='id_0-name', value='domain.local')
        self.assertFalse(self.check_that_error_message_is_correct(
            'Period characters are allowed only when '
            'they are used to delimit the components of domain style names',
            1))

    def test_012_check_regex_expression_for_git_repo_field(self):
        """Test check that validation of git repository field work
        and appropriate error message is appeared after entering incorrect url

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create Tomcat service
            3. Set "a" as a git repository url and verify error message
            4. Set "://@:" as a git repository url and verify error message
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        tomcat_id = self.get_element_id('Apache Tomcat')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.select_and_click_action_for_app('quick-add', tomcat_id)

        self.fill_field(by.By.ID, field='id_0-repository', value='a')
        self.assertTrue(self.check_that_error_message_is_correct(
            'Enter a correct git repository URL', 3))

        self.fill_field(by.By.ID, field='id_0-repository', value='://@:')
        self.assertTrue(self.check_that_error_message_is_correct(
            'Enter a correct git repository URL', 3))

    def test_013_check_validation_for_hostname_template_field(self):
        """Test check that validation of hostname template field work and
        appropriate error message is appeared after entering incorrect name

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create Telnet service
            3. Set "`qwe`" as a hostname template name and verify error message
            4. Set "host" as a hostname template name and
            check that there is no error message
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        telnet_id = self.get_element_id('Telnet')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', telnet_id)
        self.fill_field(by.By.ID, 'id_0-name', 'name')
        self.fill_field(by.By.ID, 'id_0-unitNamingPattern', '`qwe`')

        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()
        self.assertTrue(self.check_that_error_message_is_correct(
            'Enter a valid value.', 1))

        self.fill_field(by.By.ID, 'id_0-unitNamingPattern', 'host')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()

        WebDriverWait(self.driver, 10).until(lambda s: s.find_element(
            by.By.ID, 'id_1-osImage').is_displayed())

    def test_014_modify_package_name(self):
        """Test check ability to change name of the package

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select package and click on 'Modify Package'
            3. Rename package
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.select_action_for_package('PostgreSQL',
                                       'modify_package')
        self.fill_field(by.By.ID, 'id_name', 'PostgreSQL-modified')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

        self.assertTrue(self.check_element_on_page(
            by.By.XPATH, './/*[@data-display="PostgreSQL-modified"]'))

        self.select_action_for_package('PostgreSQL-modified',
                                       'modify_package')
        self.fill_field(by.By.ID, 'id_name', 'PostgreSQL')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

        self.assertTrue(self.check_element_on_page(
            by.By.XPATH, './/*[@data-display="PostgreSQL"]'))

    def test_015_modify_package_add_tag(self):
        """Test check ability to add file in composed service

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Click on "Compose Service"  and create new service
            3. Manage composed service: add file
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.select_action_for_package('PostgreSQL',
                                       'modify_package')

        self.fill_field(by.By.ID, 'id_tags', 'TEST_TAG')
        self.modify_package('tags', 'TEST_TAG')

        app_id = self.get_element_id('PostgreSQL')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.select_and_click_action_for_app('details', app_id)
        self.check_element_on_page(
            ".//*[@id='content_body']/div[2]/div/div/div[2]/div[2]/ul/li[6]",
            'TEST_TAG')

    def test_016_download_package(self):
        """Test check ability to download package from repository

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select PostgreSQL package and click on "More>Download Package"
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'download_package')

    @testtools.skip("Work in progress")
    def test_017_upload_package_add_to_env(self):
        """Test check ability to upload package to repository

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Click on "Upload Package"
            3. Select zip archive with package and category, submit form
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.click_on_package_action('upload_package')
        self.choose_and_upload_files('AppForUploadTest.zip')
        self.select_from_list('categories', 'Web')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

        self.assertTrue(self.check_element_on_page(
            by.By.XPATH, './/*[@data-display="AppForUploadTest"]'))

    def test_018_check_opportunity_to_toggle_package(self):
        """Test check ability to make package active or inactive

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select some package and make it inactive ("More>Toggle Package")
            3. Check that package became inactive
            4. Select some package and make it active ("More>Toggle Package ")
            5. Check that package became active
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'toggle_enabled')

        self.assertTrue(self.check_package_parameter(
            'PostgreSQL', '3', 'False'))

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'toggle_enabled')

        self.assertTrue(self.check_package_parameter(
            'PostgreSQL', '3', 'True'))

    def test_019_check_application_catalog_panel(self):
        """Test checks that 'Applications' panel is operable

        Scenario:
            1. Create environment
            2. Navigate to 'Application Catalog > Applications' panel
        """
        self.go_to_submenu('Applications')
        self.assertTrue(self.check_element_on_page(
            by.By.XPATH, ".//*[@id='content_body']/div[1]/h2"))

    @testtools.skip("Work in progress")
    def test_020_env_creation_form_app_catalog_page(self):
        """Test checks that app's option 'Add to environment' is operable
        when there is no previously created env. In this case creation of the
        environment should start after clicking 'Add to environment' button

        Scenario:
            1. Navigate to 'Application Catalog > Applications' panel
            2. Click on 'Add to environment' button for some application
            3. Create new environment
            4. Add application in created environment
        """
        self.go_to_submenu('Applications')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'AddToEnv')).click()

        self.fill_field(by.By.ID, 'id_name', 'test_env')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

        self.go_to_submenu('Environments')
        self.driver.find_element_by_link_text('test_env').click()
        self.assertTrue(
            self.driver.find_element_by_id('services__action_AddApplication'))

    def test_021_check_info_about_app(self):
        """Test checks that information about app is available and truly.

        Scenario:
            1. Navigate to 'Application Catalog > Applications' panel
            2. Choose some application and click on 'More info'
            3. Verify info about application
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        app_id = self.get_element_id('PostgreSQL')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.select_and_click_action_for_app('details', app_id)

        self.assertIn('PostgreSQL is a powerful', self.driver.page_source)
        self.driver.find_element_by_link_text('Requirements').click()
        self.driver.find_element_by_link_text('License').click()

    def test_022_check_search_option(self):
        """Test checks that 'Search' option is operable.

        Scenario:
            1. Navigate to 'Application Catalog > Applications' panel
            2. Click on 'Search' panel
            3. Type name of service that should be founded
            3. Click on 'Go' and check result
        """
        self.go_to_submenu('Applications')
        self.driver.find_element_by_id('MuranoSearchPanelToggle').click()
        self.fill_field(by.By.XPATH, ".//*[@name='search']", 'PARAM')
        self.driver.find_element_by_xpath(
            ".//*[@id='MuranoSearchPanel']/form/button").click()

    def test_023_filter_by_category(self):
        """Test checks ability to filter applications by category
        in Application Catalog page

        Scenario:
            1. Navigate to 'Application Catalog' panel
            2. Click on 'Category' panel
            3. Select category and click on it
            4. Verify result
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        package_category1 = self.get_element_id('PostgreSQL')
        package_category2 = self.get_element_id('Active Directory')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.driver.find_element_by_id('MuranoCategoriesPanelToggle').click()
        self.driver.find_element_by_link_text('Databases').click()

        self.assertTrue(self.check_element_on_page(
            by.By.XPATH, ".//*[@href='/{0}/murano/catalog/details/{1}']".
            format(self.url_prefix, package_category1)))

        self.driver.find_element_by_id('MuranoCategoriesPanelToggle').click()
        self.driver.find_element_by_link_text('Microsoft Services').click()

        self.assertTrue(self.check_element_on_page(
            by.By.XPATH, ".//*[@href='/{0}/murano/catalog/details/{1}']".
            format(self.url_prefix, package_category2)))

    @testtools.skip("Work in progress")
    def test_024_check_option_switch_env(self):
        """Test checks ability to switch environment and add app in other env

        Scenario:
            1. Navigate to 'Application Catalog>Environments' panel
            2. Create environment 'env1'
            3. Create environment 'env2'
            4. Navigate to 'Application Catalog>Application Catalog'
            5. Click on 'Environment' panel
            6. Switch to env2
            7. Add application in env2
            8. Navigate to 'Application Catalog>Environments'
            and go to the env2
            9. Check that added application is here
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        app_id = self.get_element_id('Telnet')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Environments')
        self.create_environment('env1')
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'env1'))
        self.create_environment('env2')
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'env1'))
        self.go_to_submenu('Applications')
        self.driver.find_element_by_id('MuranoDefaultEnvPanelToggle').click()
        self.driver.find_element_by_id('environment_switcher').click()
        self.driver.find_element_by_xpath(
            ".//*[@id='environment_list']/li[2]/a").click()

        self.create_linux_telnet('linuxtelnet', app_id)

        self.go_to_submenu('Environments')
        self.env_to_components_list('env1')
        self.assertTrue(self.check_element_on_page(by.By.LINK_TEXT,
                                                   'linuxtelnet'))

    def test_025_check_statistics_panel(self):
        """Test checks that 'Statictics' panel is operable

        Scenario:
            1. Navigate to 'Application Catalog > Statistics' panel
        """
        self.go_to_submenu('Statistics')
        self.driver.find_element_by_link_text('Murano API Servers').click()
        self.driver.find_element_by_link_text(
            'Murano Instance Statistics').click()

    def test_026_modify_description(self):
        """Test check ability to change description of the package

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select package and click on 'Modify Package'
            3. Change description
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.select_action_for_package('PostgreSQL',
                                       'modify_package')

        self.modify_package('description', 'New Description')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.check_element_on_page(
            ".//*[@class='app-description']",
            'New Description')

    def test_027_check_opportunity_to_delete_package(self):
        """Test check ability to delete package from database

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select some package
            3. Delete this package
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        package = self.get_element_id('PostgreSQL')
        self.select_and_click_element(package)

        self.click_on_package_action('delete_package')
        self.confirm_deletion()
        self.assertFalse(self.check_element_on_page(
            by.By.XPATH, './/*[@data-display="PostgreSQL"]'))
