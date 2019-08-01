from utilities import *
from scrapy.crawler import CrawlerProcess
from mutual_fund_spider import MutualFundsSpider
import sys
import logging


# Change the logging format to this custom one
logging.basicConfig(format='(%(asctime)s) %(levelname)s: %(message)s', level=logging.INFO)

# Declare variables
depth = 1
cik = None
test_mode = False

make_13f_dir()

# Check for command-line arguments
if sys.getsizeof(sys.argv) > 1:
    for arg in sys.argv:
        if arg.startswith('-'):
            if '=' in arg:
                arg = arg[1::].split('=')
                arg_name = arg[0].lower()
                arg_value = arg[1]
            else:
                arg = arg[1::]
                arg_name = arg.lower()
                arg_value = None

            if arg_name == 'ticker':
                try:
                    cik = arg_value.split('|')[1].strip()
                except IndexError:
                    cik = None
                    logging.warn(f'The ticker you entered ({arg_value}) is not properly formatted: \"Name | CIK\"')
                    sys.exit()
            elif arg_name == 'cik' and arg_value is not None:
                cik = arg_value
            elif arg_name == 'depth' and arg_value is not None:
                try:
                    depth = int(arg_value)
                except ValueError:
                    logging.warn("Argument \'depth\' must be an integer")
                    sys.exit()
            elif arg_name == 'test':
                logging.info("-depth cannot be set in test mode")
                test_mode = True
            else:
                logging.warn(f'{arg} is not a valid argument')

if test_mode:
    # Run parallel processes
    run_test()
else:
    # Run a single process
    process = CrawlerProcess()
    process.crawl(MutualFundsSpider, depth=depth, cik=cik)
    process.start()
