from test_data import test_data
from twisted.internet import reactor
from scrapy.crawler import CrawlerRunner
from mutual_fund_spider import MutualFundsSpider
import os
import sys
import logging


def log_error(subject, message, error=False):
    print(f'\nError ({subject}): {message}') if error else print(f'({subject}): {message}\n')


def make_13f_dir():
    """
    Create the 13F_Reports directory if it doesn't already exist

    :return: None
    """

    if not os.path.exists("./13F_Reports/"):
        try:
            os.makedirs("./13F_Reports/")
        except OSError:
            logging.error('__init__', 'Unable to create 13F_Reports directory... Try manually creating a directory named \"13F_Reports\" and try again')
            sys.exit()


def run_test():
    """
    Runs an asynchronous crawler process for every ticker in test_data in parallel

    :return: None
    """

    runner = CrawlerRunner()

    for index, test in enumerate(test_data):
        temp = test.split('|')

        try:
            int(temp[0].strip())
            test_cik = temp[0].strip()
        except ValueError:
            test_cik = temp[1].strip()

        runner.crawl(MutualFundsSpider, depth=1, cik=test_cik)

    deferred = runner.join()
    deferred.addBoth(lambda _: reactor.stop())
    reactor.run()
