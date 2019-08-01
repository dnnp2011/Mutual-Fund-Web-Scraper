# **Dalton Pierce** - *Plaid Code Challenge*
<hr/>


## Overview
Given a valid CIK, this program will parse and write 13F report XML documents to a .tsv file, as well as search summary information from primary_doc.xml to a separate .tsv shared among all searched funds. To accomplish this, I used the web crawling library: Scrapy. My custom Scrapy "Spider" contains logic that determines the currently browsed page (in a headless client) using specially crafted XPath queries to locate important page landmarks. After determining the current page, my Spider generates a next_url string based on scraped hrefs and yields a new Scrapy.Request for that URL. This cycle of determining the current page, collecting data, and generating a URL for the next link in the page-chain is the foundation of this program. Upon reaching one of the target XML documents (either primary_doc.xml or the 13fholdings.xml (name varies)), one of the xml_parser functions is invoked to parse and write their respective documents to TSV files. When parsing primary_doc.xml, headers (extracted from tag names) are preserved between inconsistent form variants by parsing headers from existing search_summary.tsv file into Python objects, merging it with new headers and overwriting the old data. The parsing functions in xml_parser.py use BeautifulSoup (and lxml parsing API) to break down the raw XML into a navigable object that can be queried and modified. One important step the parsers take is to replace sections with redundant or ambiguous tag names, with copies whose tags have been joined the tag names of their direct parents. The result of which is a unique tag name that won't be overwritten by other tags of the same name. The last step in this process is to turn the objects that have been built from collected data into individual lines and write them to a .tsv file.



## Getting Started:
#### I've tested this program in both Windows and Linux environments. Be aware that Windows in particular requires an additional dependency (due to the Twisted package).

If you're running a Linux environment:
* Install python3 **```sudo apt-get install python3```**
* Install python3.6-dev **```sudo apt-get install python3.6-dev```**
* Install python3-pip **```sudo apt-get install python3-pip```**
* Install python3-venv **```sudo apt-get install python3-venv```**
* Create new virtual env **```python3 -m venv dalton-pierce-env```**
* Activate the virtual env **```source dalton-pierce-env/bin/activate```**
* Install dependencies **```pip3 install -r requirements.txt```**
* Execute the program **```python3 main.py```** or **```python3 main.py -cik=<Fund CIK>```**
* Leave the virtual env: **```deactivate```**

If you're running a Windows environment:
* Install python3 and pip: download from [https://www.python.org/downloads/release/python-374/]("https://www.python.org/downloads/release/python-374/")
* Install python3-venv: **```python -m pip install --user virtualenv```**
* Create new virtual env: **```python -m venv dalton-pierce-env```**
* Activate the virtual env: **```.\dalton-pierce-env\Scripts\activate```**
* Install dependencies: **```pip install -r requirements.txt```**
* Windows machines require an additional "pywin32" dependency: **```pip install pywin32```**
* Execute the program: **```python main.py```** or **```python main.py -cik=<Fund CIK>```**
* Leave the virtual env: **```deactivate```**



## How To Use
1. Method 1: Interactive Prompt
    * Run **`python3 main.py`**
    * A prompt will appear asking that you enter a CIK, or ticker in the format "Name | CIK", provide the information and press enter.
    
2. Method 2: Command-Line Arguments
    * Run with optional arguments: **`-test -cik=<int> -depth=<int/str> -ticker=<str>`**. This will bypass the interactive prompt and immediately begin crawling.
    * **`-cik=<int/str>`** an integer or string representing a mutual fund's Central Index Key. If both the **`-cik`** and **`-ticker`** flags are passed, the **`-cik`** value will take precedence.
    * **`-depth<int/str>`** an integer or string representing the number of most recent reports for the given fund to return
    * **`-ticker<str>`** a string containing the name and CIK for a fund. Only the CIK is extracted due to names being an inconsistent search parameter.
    * **`-test`**  Passed values are ignored. Indicates that the program should a parallel process for every ticker in test_data.py; Other flags are ignored when this flag is passed.
    
    #### Examples:
    * **`python3 main.py -test`**: Return the latest report for each ticker in test_data.py (NOTE: In the original email, the CIK of ticker "Caledonia | 0001166559" was a repeat of the Gates Foundation CIK, and the name was ambiguous. I used my best judgement to infer the ticker: "CALEDONIA INVESTMENTS PLC | 0001037766" was likely intended)
    * **`python3 main.py -cik=0001397545`** Return the latest report for the given CIK
    * **`python3 main.py -cik=0001397545 -depth=5`** Return the latest 5 reports for the given CIK
    * **`python3 main.py -ticker="Kemnay Advisory Services Inc. | 0001555283"`** Return the latest report for the given ticker



## Features
* Option to provide CIK via interactive prompt, or command-line arguments.

* Ability to parse reports that are not the most recent using **`-depth`** flag.

* Using the **`-test`** flag automatically runs a new Spider for each entry in _*`./test_data.py`*_, 
avoiding the need to manually enter each CIK or ticker.

* Enabling **`-test`** mode allows all the Spider processes to run in parallel.

* Gracefully handles different report formats by using existing TSV files as a source of previously parsed headers, then merging it with new headers, and preserving tab-spacing for entries missing that tag by adding "N/A" placeholders.

* Generates a single TSV spreadsheet for each individual 13F Report, as well as a shared search_summary TSV file that compiles generalized information for every mutual fund searched.

* Gracefully handles tag variants (like those beginning with _*`ns1:`*_).

* Gracefully handles name variations for the target 13F Holdings Report (by looking for a file ending in .xml that is not primary_doc.xml).

* Collapses the names of ambiguous tags (like "name") with their parents, thereby preserving hierarchy and creating a unique tag name (**`<name>`** becomes **`<filer_credentials_name>`**). Using this technique, I was able to compress the hierarchical data of XML into the flat structure of TSV files.

* Gracefully handles many edge-cases or typos (such as invalid CIKs, tickers, and reversed ticker order).


## Bugs
* When running in **`-test`** mode, sometimes an error is thrown from the dependency "Twisted" due to special functionality utilized in the run_test() function. As far as I can tell, it's random and can often be corrected by simply running the program again

* Disabled ability to search with only the fund name to avoid name ambiguity problems, and errors due to lower/uppercase letters, missing punctuation, or url encoded characters (ex. "\&amp;" in "BILL & MELINDA GATES FOUNDATION TRUST").

* Combining the -test and -depth command-line arguments cause strange results (disabled to prevent errors).

* The manner in which dates are applied to 13f_report filenames is such that, given the asynchronous nature of parallel Scrapy requests, it could lead to race conditions that apply the wrong date to a filename. Some solutions could be to make the requests synchronous at the cost of run-time or use key-value pairs to ensure matching dates against some other consistent metric.

* Logging messages are mixed in with the deluge of other logs produced by Scrapy and may require scrolling up and scanning through the logs to find error messages and warnings.

* If the class or id of certain landmark HTML elements (like **`id="contentDiv"`**) were changed, the XPath queries used to determine the current page may break.



## Fetching older reports
This program is capable of fetching reports older than the most recent using the **`-depth=<int>`** [command-line argument](#how-to-use), however, using the depth flag while in **`-test`** mode causes strange results due to a bug, and has therefore been disabled in this mode.



## Problems I ran into:
* Compressing the complex data of XML hierarchy into a flat data structure without ambiguity
* Keeping track of my position in the page chain
* Dealing with naming inconsistency and form variations
* Learning to use Scrapy, and BeautifulSoup
* Running multiple Scrapy CrawlerProcess() instances in parallel
* How to preserve headers (headers are just extracted tag names placed as row headers in the TSV file) that aren't shared between every primary_doc.xml entry
* How to format the objects representing each report or summary entry into lines that can be written to a TSV document
* How to get an entry point as close to the destination URL as possible

