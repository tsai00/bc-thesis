import pandas as pd

from selenium import webdriver
from selenium.webdriver import Proxy
from selenium.webdriver.common.proxy import ProxyType


class WebScraper:

    def __init__(self, file_input, file_used_ids, file_proxies):
        self.input_file = file_input
        self.file_used_ids = file_used_ids
        self.file_proxies = file_proxies

        self._used_ids = []     # List with IDs of previously scraped listings

    @staticmethod
    def add_column_with_links(input_data):
        url_base = 'https://www.bezrealitky.cz/nemovitosti-byty-domy/'

        input_data['url'] = input_data['uri'].apply(lambda x: url_base + x)

        return input_data

    def make_list_with_used_ids(self, file_used_ids):
        df = pd.read_excel(file_used_ids)
        self._used_ids.extend(df['id'].tolist())


    @staticmethod
    def get_proxy_list(proxies_file):
        proxies = pd.read_table(proxies_file, delim_whitespace=True, header=None)[0].values.tolist()

        return proxies

    @staticmethod
    def set_browser(proxy_input):

        capabilities = webdriver.DesiredCapabilities.CHROME

        # Set up proxy
        if proxy_input is not None:
            try:
                proxy = Proxy()
                proxy.proxy_type = ProxyType.MANUAL
                proxy.http_proxy = proxy_input
                proxy.ssl_proxy = proxy_input

                proxy.add_to_capabilities(capabilities)
            except:
                pass

        options = webdriver.ChromeOptions()

        # Do not show browser GUI
        options.add_argument('--headless')

        driver = webdriver.Chrome(desired_capabilities=capabilities, options=options)

        return driver


