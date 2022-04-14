import pandas as pd
import random
import logging
import datetime

from selenium import webdriver
from selenium.webdriver import Proxy
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import ProxyType
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Configuring file for logs
logging.basicConfig(filename='web_scraper.log',
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    datefmt='%d.%m.%Y %H:%M:%S')


class WebScraper:
    def __init__(self, file_input: str, file_used_ids: str = '', file_proxies: str = '') -> None:
        self.input_file = file_input
        self.file_used_ids = file_used_ids
        self.file_proxies = file_proxies

        self._used_ids = []     # List with IDs of previously scraped listings

    @staticmethod
    def add_column_with_links(input_data: pd.DataFrame) -> pd.DataFrame:
        url_base = 'https://www.bezrealitky.cz/nemovitosti-byty-domy/'

        input_data['url'] = input_data['uri'].apply(lambda x: url_base + x)

        return input_data

    def make_list_with_used_ids(self, file_used_ids: str) -> None:
        df = pd.read_excel(file_used_ids)
        self._used_ids.extend(df['id'].tolist())

    def scrape_details(self, input_data: pd.DataFrame, proxies: list) -> (pd.DataFrame, list):
        logging.info('Scraping started')
        print(f'[{datetime.datetime.now()}] Scraping started')

        if proxies is None:
            proxies = []

        scraped_data = []  # List with final data
        bad_proxies = set()  # List with not working proxies

        # Iterating through data
        for i, row in input_data.iterrows():

            listing_id = row['id']  # ID of listing
            url = row['url']  # URL of listing

            if listing_id in self._used_ids:
                continue

            parameters = {'id': listing_id, 'url': url}

            # Pick random proxy
            proxy = random.choice(proxies) if proxies else None

            browser = self.set_browser(proxy)

            is_browser_working = False

            while not is_browser_working:
                try:
                    browser.get(url)
                    is_browser_working = True
                except:
                    bad_proxies.add(proxy)

                    browser.close()
                    proxy = random.choice(proxies) if proxies else None

                    while proxy in bad_proxies:
                        proxy = random.choice(proxies) if proxies else None

                    browser = self.set_browser(proxy)

            # Handle popup window
            try:
                WebDriverWait(browser, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[@id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']"))).click()
            except:
                pass

            #### SCRAPING PARAMETERS SECTION ####
            try:
                parameters_area = browser.find_element(By.XPATH, '//div[@id="detail-parameters"]')
                params = parameters_area.find_elements(By.XPATH, './/div[@class="row param"]')

                for param in params:
                    try:
                        title = param.find_element(By.XPATH, './*[1]').text.strip().replace('\n', '')   # Parameter's title
                        value = param.find_element(By.XPATH, './*[2]').text.strip().replace('\n', '')   # Parameter's value

                        # Drop irrelevant parameters
                        if title not in ['Investiční rádce', 'Energie', 'Internet']:
                            parameters.update({title: value})    # Add title:value to listing details
                    except:
                        continue
            except Exception as e:
                logging.error(f'Error while scraping details on page {i} ({listing_id})')
                print(f'[{datetime.datetime.now()}] Error while scraping details on page {i} ({listing_id}) - {e}')
                continue
            #### END OF SCRAPING PARAMETERS SECTION ####

            #### SCRAPING NEIGHBORHODD INFO SECTION ####
            try:
                neighborhood_area = browser.find_element(By.XPATH, '//div[@id="detail-pois"]')
                neighborhood_params = neighborhood_area.find_elements(By.XPATH, './/div[@class="poi-item__content"]')

                for param in neighborhood_params:
                    try:
                        title = param.find_element(By.XPATH, './/span[@class="poi-item__name--type"]').text.replace(':', '')     # Parameter's title
                        value = param.find_element(By.XPATH, './/div[@class="poi-item__walking" or @class="poi-item__driving"]/strong').text     # Parameter's value

                        parameters.update({title: value})   # Add title:value to listing details
                    except:
                        continue
            except:
                logging.error(f'Error while scraping area info on page {i} ({listing_id})')
                print(f'[{datetime.datetime.now()}] Error while scraping area info on page {i} ({listing_id})')
                continue
            #### END OF SCRAPING NEIGHBORHODD INFO SECTION ####

            # Add listing with details to scraped data
            scraped_data.append(parameters)

            # Add ID of scraped listing to used IDs
            self._used_ids.append(listing_id)

            logging.info(f'Page {i} (ID: {listing_id}) scraped')
            print(f'[{datetime.datetime.now()}] Page {i} (ID: {listing_id}) scraped')

            browser.close()

        logging.info(f'Scraping is done: {len(scraped_data)} listings were exported')
        print(f'[{datetime.datetime.now()}] Scraping is done: {len(scraped_data)} listings were exported')

        # Converting to DataFrame
        try:
            scraped_data = pd.DataFrame(scraped_data)
            scraped_data = input_data.merge(scraped_data, on='id')
        except Exception as e:
            logging.error(f'Error while converting scraped data to DataFrame: {e}')
            print(f'[{datetime.datetime.now()}] Error while converting scraped data to DataFrame: {e}')

        return scraped_data

    @staticmethod
    def get_proxy_list(proxies_file: str) -> list:
        proxies = pd.read_table(proxies_file, delim_whitespace=True, header=None)[0].values.tolist()

        return proxies

    @staticmethod
    def set_browser(proxy_input: str = None) -> webdriver:
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

    def run_scraper(self) -> None:
        # Load input data
        try:
            input_data = pd.read_excel(self.input_file)
            data = self.add_column_with_links(input_data)
        except FileNotFoundError:
            logging.error(f'Error while loading input data: file {self.input_file} does not exist')
            print(f'[{datetime.datetime.now()}] Error while loading input data: file {self.input_file} does not exist')
            return
        except KeyError:
            logging.error(f'Error while loading input data: could not find column "uri" in file {self.file_used_ids}')
            print(f'[{datetime.datetime.now()}] Error while loading input data: could not find column "uri" in file {self.file_used_ids}')
            return
        except Exception as e:
            logging.error(f'Error while loading input data: {e}')
            print(f'[{datetime.datetime.now()}] Error while loading input data: {e}')
            return

        # Load previously scraped data
        if self.file_used_ids:
            try:
                self.make_list_with_used_ids(self.file_used_ids)
            except FileNotFoundError:
                logging.error(f'Error while loading used IDs: file {self.file_used_ids} does not exist')
                print(
                    f'[{datetime.datetime.now()}] Error while loading used IDs: file {self.file_used_ids} does not exist')
            except KeyError:
                logging.error(f'Error while loading used IDs: could not find column "id" in file {self.file_used_ids}')
                print(
                    f'[{datetime.datetime.now()}] Error while loading used IDs: could not find column "id" in file {self.file_used_ids}')
            except Exception as e:
                logging.error(f'Error while loading used IDs: {e}')
                print(f'[{datetime.datetime.now()}] Error while loading used IDs: {e}')

        # Load proxies
        if self.file_proxies:
            try:
                proxies = self.get_proxy_list(self.file_proxies)
            except KeyError:
                logging.error(f'Error while loading proxies: file {self.file_proxies} does not exist')
                print(
                    f'[{datetime.datetime.now()}] Error while loading proxies: file {self.file_proxies} does not exist')
                proxies = []
            except Exception as e:
                logging.error(f'Error while loading proxies: {e}')
                print(f'[{datetime.datetime.now()}] Error while loading proxies: {e}')
                proxies = []
        else:
            proxies = None

        # Scrape data
        scraped_data = self.scrape_details(data, proxies)

        # Configuring current time to name the file
        now = datetime.datetime.now()
        dt_string = now.strftime("%d_%m_%Y_%H_%M")

        # Exporting data
        try:
            used_ids_df = pd.DataFrame(self._used_ids, columns=['id'])
            used_ids_df.to_excel(f'used_ids_{dt_string}.xlsx')
            scraped_data.to_excel(f'scraped_data_{dt_string}.xlsx')
        except Exception as e:
            logging.error(f'Error while exporting data: {e}')
            print(f'[{datetime.datetime.now()}] Error while scraping data: {e}')
