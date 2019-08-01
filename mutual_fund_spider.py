import scrapy
import logging
from utilities import *
from xml_parser import *


class MutualFundsSpider(scrapy.Spider):
    """
    Scrapy Spider responsible for collecting information on the desired mutual fund from the user, and using that information to scrape and crawl the SEC's EDGAR system.

    :var name (str): Name of this Spider, for Scrapy reference
    :var start_urls ([str]): Starting point of the Spider's crawl
    :var allowed_domains ([str]): Scrapy will only crawl URLs within these domains
    :var fund_cik (str | None): Mutual Fund Central Index Key collected from the user
    :var fund_name (str | None): Mutual Fund Name collected from the user

    :returns (str): Either the raw XML from the target document, or an error message
    """

    # Declare class fields
    name = "MutualFundsSpider"
    start_urls = []
    allowed_domains = ["www.sec.gov"]
    fund_cik = None
    fund_name = None
    date_filed = None
    depth = 1
    filing_dates = []
    filed_reports = []
    primary_doc_parsed = False
    last_date = []

    # Define constructor
    def __init__(self, **kwargs):
        """
        Generates the Spider's start_urls based on user input

        :param kwargs: Constructor params, if any
        :var user_input (str): The mutual fund name and/or CIK collected from user
        """

        super().__init__(**kwargs)

        user_input = None

        if len(kwargs) > 0:
            if 'depth' in kwargs and kwargs['depth'] is not None and kwargs['depth'] > 1:
                self.depth = kwargs['depth']
            if 'cik' in kwargs and kwargs['cik'] is not None:
                user_input = kwargs['cik']

        if user_input is None:
            print('Enter the CIK, Mutual Fund Name, or both in the format \"Name | CIK\": \n')
            user_input = input().strip()

        if "|" in user_input:
            temp = user_input.split("|")
            try:
                int(temp[0].strip())
                self.fund_cik = temp[0].strip()
                self.fund_name = temp[1].strip()
            except ValueError:
                self.fund_cik = temp[1].strip()
                self.fund_name = temp[0].strip()
        else:
            try:
                int(user_input)
                self.fund_cik = user_input
                self.fund_name = None
            except ValueError:
                self.fund_name = user_input
                self.fund_cik = None

        if self.fund_cik is not None:
            url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={self.fund_cik}&type=&dateb=&owner=exclude&count=100'
            self.start_urls = [url]
        elif self.fund_name is not None:
            url = f'https://www.sec.gov/cgi-bin/browse-edgar?company={self.fund_name}&owner=exclude&action=getcompany'
            self.start_urls = [url]
        else:
            logging.warning('Invalid Company Name or CIK number, please check your input and try again...')


    def start_requests(self):
        """
        Iterates through start_urls, yielding a new Scrapy request for each one

        :return (Request): New Scrapy request that navigates to the given URL
        """

        # Yield a new Scrapy Request for each start_url
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)


    def parse_depth(self, response):
        """
        Used for parsing a series of holding reports when the depth command-line parameter is passed

        :param response: The Scrapy Response object
        """

        logging.info(f'Crawling URL in --depth mode: {response.url}')

        # Determine the current page
        # Reached the Filing Details Page in -depth mode
        if response.xpath('//div[@id="headerBottom"]/div[@id="PageTitle" and contains(text(), "Filing Detail")]') and "index.htm" in response.url:
            logging.info('Reached the Filing Detail Page in -depth mode')

            # Query the URLs of the target documents
            primary_doc_url = response.urljoin(response.xpath('//div[@id="contentDiv"]//table[@class="tableFile"]//tr [td[3] [a [text()="primary_doc.xml"]]] /td[3]/a/@href').get())
            holdings_report_url = response.urljoin(
                response.xpath('//div[@id="contentDiv"]//table[@class="tableFile"]//tr [td[3] [a [contains(text(), ".xml")]] and td[4] [contains(text(), "INFORMATION TABLE") or contains(text(), "information table")]] /td[3]/a/@href').get())

            # Generate a request for the primary_doc.xml and 13fInfoTable.xml URLs
            for i in range(2):
                # Check if the primary_doc has already been parsed to avoid overwriting unnecessarily
                if i == 0:
                    yield scrapy.Request(primary_doc_url, callback=self.parse)
                elif i == 1:
                    self.last_date.append(
                        response.xpath('//div[@id="contentDiv"]//div[@class="formContent"]//div[@class="formGrouping"]//div [@class="infoHead" and contains(text(), "Filing Date")]/following-sibling::div/text()').get().replace('-', '_').strip())
                    yield scrapy.Request(holdings_report_url, callback=self.parse_depth)

        # Reached the 13F Holdings Report XML document
        elif ".xml" in response.url:
            logging.info('Reached the target 13F Holdings Report in -depth mode')

            # Append this report to filed_reports list
            self.filed_reports.append(response.body)

            # If this report is the last one needed, loop through filed_reports and parse them
            if len(self.filed_reports) is self.depth:
                try:
                    for n, report in enumerate(self.filed_reports):
                        parse_info_table(report, self.fund_cik, self.last_date[n])
                except IndexError:
                    logging.error("Index is out of range. filed_reports and last_date should be the exact same length.")


    def parse(self, response):
        """
        Parses the current page. Determines what page in the chain the Spider is currently crawling, and responds the next page in the chain, an error message, or the target document XML

        :param response: The Scrapy Response object
        :return:
        """

        logging.info(f'Crawling URL: {response.url}')

        # The entered CIK or Name was invalid, print an error message
        if response.xpath('//div[@id="contentDiv"]/div[contains(text(), "No matching")]') or response.xpath('//h1[contains(text(), "No matching")]'):
            logging.error('Invalid Company Name or CIK number, please check your input and try again...')

        # Reached the filings page, find the most recent 13F entry and follow to filing details
        elif (self.fund_cik is not None or self.fund_name is not None) \
                and response.xpath(f'//div[@id="contentDiv"]//span[@class="companyName" and (contains(text(), "{self.fund_name}") or //a[contains(@href, "CIK={self.fund_cik}")])]') \
                and response.xpath('//div[@id="headerBottom"]/div[@id="PageTitle" and contains(text(), "EDGAR Search Results")]'):

            logging.info('Reached the Filings Page')
            if not self.fund_cik:
                self.fund_cik = response.xpath('//div[@id="contentDiv"]//span[@class="companyName"]/a/text()').get().split(' ')[0].strip()

            if self.depth > 1:
                # Find the last depth number of holding reports
                reports = response.xpath('//div[@id="seriesDiv"]/table//tr [td[1] [contains(text(), "13F") and contains(text(), "HR")]] //td[2]//a//@href')
                max_depth = len(reports)

                # Make sure depth isn't greater than the number of 13F forms on this page. Unable to handle turning pages yet.
                if self.depth > max_depth:
                    self.depth = max_depth

                # Take self.depth number of reports from the list
                reports = reports[0:self.depth]

                # Get the filing dates for each report and push it to the filing_dates field
                dates = response.xpath('//div[@id="seriesDiv"]/table//tr [td[1] [contains(text(), "13F") and contains(text(), "HR")]] //td[4]//text()')[0:self.depth]
                for date in dates:
                    self.filing_dates.append(date.get().replace('-', '_').strip())

                # Iterate over each report and generate a new request for the Filing Detail page
                for report in reports:
                    next_url = response.urljoin(report.get())
                    # Uses the parse_depth function as callback, as depth searches must be handled differently
                    yield scrapy.Request(next_url, callback=self.parse_depth)

            else:
                # Save date_filed to class field for non-depth searches
                if not self.date_filed:
                    self.date_filed = response.xpath('//div[@id="seriesDiv"]/table//tr [td[1] [contains(text(), "13F") and contains(text(), "HR")]] /td[4]/text()').get().replace('-', '_').strip()

                next_url = response.urljoin(response.xpath('//div[@id="seriesDiv"]/table//tr [td[1] [contains(text(), "13F") and contains(text(), "HR")]] /td[2]/a/@href').get())
                yield scrapy.Request(next_url, callback=self.parse)

        # Reached the name results page. This means the entered name is not written EXACTLY as it is on EDGAR. Check for CIK to compensate
        elif self.fund_name is not None and response.xpath(f'//div[@id="contentDiv"]/span[@class="companyMatch" and contains(text(), "Companies with names matching")]'):
            if self.fund_cik is not None:
                next_url = response.urljoin(response.xpath(f'//div[@id="seriesDiv"]/table//tr [td[1] [a [text()="{self.fund_cik}"]]] /td[1]/a/@href').get())
                yield scrapy.Request(next_url, callback=self.parse)
            else:
                logging.warning('The Fund Name you entered is ambiguous. Make sure the name is spelled EXACTLY as it is on EDGAR, or enter a CIK.')

        # Reached the filing detail page for the most recent 13F - HR report, and the primary_doc.xml summary document and follow their links
        elif response.xpath('//div[@id="headerBottom"]/div[@id="PageTitle" and contains(text(), "Filing Detail")]') and "index.htm" in response.url:
            logging.info('Reached the Filing Detail Page')

            primary_doc_url = response.urljoin(response.xpath('//div[@id="contentDiv"]//table[@class="tableFile"]//tr [td[3] [a [text()="primary_doc.xml"]]] /td[3]/a/@href').get())
            holdings_report_url = response.urljoin(
                response.xpath('//div[@id="contentDiv"]//table[@class="tableFile"]//tr [td[3] [a [contains(text(), ".xml")]] and td[4] [contains(text(), "INFORMATION TABLE") or contains(text(), "information table")]] /td[3]/a/@href').get())

            # Generate a request for the primary_doc.xml and 13fInfoTable.xml URLs
            for i in range(2):
                if i == 0:
                    yield scrapy.Request(primary_doc_url, callback=self.parse)
                elif i == 1:
                    yield scrapy.Request(holdings_report_url, callback=self.parse)

        # Reached the summary document, pass to parser utility and write to file
        elif "primary_doc.xml" in response.url:
            logging.info('Reached the \'primary_doc.xml\' Document')
            parse_primary_doc(response.body)
            # TODO: Create a utility parser to turn raw XML into TSV and write to file
        # Reached the 13F holdings document, pass to parser utility and write to file
        elif ".xml" in response.url:
            logging.info('Reached the target 13F Holdings Report')
            parse_info_table(response.body, self.fund_cik, self.date_filed)
        else:
            logging.debug('Reached an unrecognized page')
