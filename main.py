from web_scraper import WebScraper
import datetime

if __name__ == '__main__':
    print('STARTED ON:', datetime.datetime.now())

    webscraper = WebScraper(file_input='input.xlsx', file_used_ids='used_ids.xlsx', file_proxies='proxies.txt')

    webscraper.run_scraper()

    print('DONE ON:', datetime.datetime.now())