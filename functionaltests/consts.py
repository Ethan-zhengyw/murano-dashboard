ButtonSubmit = ".//*[@name='wizard_goto_step'][2]"
InputSubmit = "//input[@type='submit']"
ConfirmDeletion = ".//*[@id='modal_wrapper']/div/div[3]/a[1]"
More = "/html/body/div/div[2]/div[3]/form/table/tbody/tr/td[4]/div/a[2]"
Murano = "//*[@id='main_content']/div[2]/div/dl/dt[3]/div"
Application_Catalog = "//*[@id='main_content']/div[2]/div/dl/dd[3]/div[1]/h4/div"  # noqa
Manage = "//*[@id='main_content']/div[2]/div/dl/dd[3]/div[2]/h4/div"
CategorySelector = "//a[contains(text(), '{0}')][contains(@class, 'dropdown-toggle')]"  # noqa
App = "//div[contains(@class, 'app-list')]//h4[contains(text(), '{0}')]"
MockAppDescr = "//div[h4[contains(text(), 'MockApp')]]/p"
AppPackageDefinitions = "//tr[@data-display='{0}']"
TagInDetails = "//div[contains(@class, 'app-meta')]//ul//li[strong[contains(text(), 'Tags')]]"  # noqa
TestImage = "//tr[td[contains(text(), 'New Image')]]"
DeleteImageMeta = TestImage + "//td//button[contains(text(), 'Delete Metadata')]"  # noqa
ImageMeta = "//dl[dt[contains(text(), 'murano_image_info')]]/dd"
More = "//tr[@id='murano__row__{0}']//a[@data-toggle='dropdown']"
