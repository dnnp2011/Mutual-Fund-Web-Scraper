from bs4 import BeautifulSoup
from utilities import *
import logging
import csv


def parse_info_table(raw_xml, fund_name, date):
    """
    Parses the 13F Holdings Report XML document, and writes it to a .tsv file.

    The reports are named in the following format: <cik>_13f_holdings_<periodOfReport>

    :param raw_xml: The raw XML object to be parsed
    :param fund_name: The name of the filer
    :param date: The period of this report
    """

    soup = BeautifulSoup(raw_xml, 'lxml')

    # Check for a variant of tag names prepended by ns1:
    info_tables = soup.find_all('infotable')
    if not info_tables:
        info_tables = soup.find_all('ns1:infotable')

    headers = []
    processed_tables = []

    # Iterate through each info table, and replace prepend parent tag name onto children to avoid losing hierarchy data
    for table in info_tables:
        new_table = { }

        if table.find('votingauthority') is not None:
            table.find('votingauthority').replace_with(BeautifulSoup(f"""
            <votingauthority>
                {f"<votingauthority_sole>{table.votingauthority.find('sole').text}</votingauthority_sole>" if table.votingauthority.find('sole') else ""}
                {f"<votingauthority_shared>{table.votingauthority.find('shared').text}</votingauthority_shared>" if table.votingauthority.find('shared') else ""}
                {f"<votingauthority_none>{table.votingauthority.find('none').text}</votingauthority_none>" if table.votingauthority.find('none') else ""}
            </votingauthority>
            """, 'xml'))

        elif table.find('ns1:votingauthority') is not None:
            vauth = table.find('ns1:votingauthority')
            table.find('ns1:votingauthority').replace_with(BeautifulSoup(f"""
            <votingauthority>
                {f"<votingauthority_sole>{vauth.find('ns1:sole').text}</votingauthority_sole>" if vauth.find('ns1:sole') else ""}
                {f"<votingauthority_shared>{vauth.find('ns1:shared').text}</votingauthority_shared>" if vauth.find('ns1:shared') else ""}
                {f"<votingauthority_none>{vauth.find('ns1:none').text}</votingauthority_none>" if vauth.find('ns1:none') else ""}
            </votingauthority>
            """, 'xml'))

        # Find all XML tags that have text but no children
        for tag in table.findAll(lambda element: element.text is not None and not element.findAll()):
            # Remove ns1: from the tag names that will become TSV headers
            name = tag.name.split(':')[1] if 'ns1' in tag.name else tag.name
            if name not in headers:
                headers.append(name)
            new_table[name] = tag.text.strip()

        processed_tables.append(new_table)

    # Write the headers and each processed info table into the .tsv file as a new line
    try:
        with open(f'./13F_Reports/{fund_name.lower().strip()}_13f_holdings_{date.lower().strip()}.tsv', 'wt') as tsv_file:
            tsv_writer = csv.writer(tsv_file, delimiter='\t')
            tsv_writer.writerow(headers)

            for table in processed_tables:
                row_builder = []
                for header in headers:
                    if header in table:
                        row_builder.append(table[header])
                    else:
                        # If this report is missing a tag name that another report has, fill it with N/A placeholder
                        row_builder.append('N/A')
                tsv_writer.writerow(row_builder)
    except IOError:
        logging.debug(f'Failed to create ./13F_Reports/{fund_name.lower().strip()}_13f_holdings_{date.lower().strip()}.tsv')


def parse_primary_doc(raw_xml):
    """
    Parses the primary_doc.xml document and appends or overwrites its values to search_summary.tsv

    :param raw_xml: The raw XML object to be parsed
    """

    soup = BeautifulSoup(raw_xml, 'lxml')

    headers = []
    existing_funds = []
    new_fund = { }
    found_existing = False

    # Get the existing headers and summary data if the search_summary.tsv file is already populated to maintain consistent headers
    try:
        with open("./13F_Reports/search_summary.tsv", "rt") as tsv_file:
            reader = csv.reader(tsv_file, delimiter='\t')
            for n, line in enumerate(reader):
                if n == 0:
                    headers = line
                else:
                    line_entry = { }
                    for t, header in enumerate(headers):
                        line_entry[header] = line[t]
                    existing_funds.append(line_entry)
    except IOError:
        logging.info('No existing mutual_fund_summary.tsv file found, creating new one...')

    # Modify the tree to flatten the important sections with repeating tag names by prepending them with the tag names of their parents. Thereby preserving hierarchy in a flat structure
    soup.filer.replace_with(BeautifulSoup(f"""
    <filer>
        {f"<filer_cik>{soup.filer.credentials.find('cik').text.strip()}</filer_cik>" if soup.filer.credentials.find('cik') else ""}
        {f"<filer_ccc>{soup.filer.credentials.find('ccc').text.strip()}</filer_ccc>" if soup.filer.credentials.find('ccc') else ""}
    </filer>
    """, 'xml'))
    soup.filingmanager.replace_with(BeautifulSoup(f"""
    <filingmanager>
        {f"<filingmanager_name>{soup.filingmanager.find('name').string}</filingmanager_name>" if soup.filingmanager.find('name') else ""}
        {f"<filingmanager_address_street1>{soup.filingmanager.address.find('ns1:street1').text.strip()}</filingmanager_address_street1>" if soup.filingmanager.address.find('ns1:street1') else ""}
        {f"<filingmanager_address_street2>{soup.filingmanager.address.find('ns1:street2').text.strip()}</filingmanager_address_street2>" if soup.filingmanager.address.find('ns1:street2') else ""}
        {f"<filingmanager_address_city>{soup.filingmanager.address.find('ns1:city').text.strip()}</filingmanager_address_city>" if soup.filingmanager.address.find('ns1:city') else ""}
        {f"<filingmanager_address_stateorcountry>{soup.filingmanager.address.find('ns1:stateorcountry').text.strip()}</filingmanager_address_stateOrCountry>" if soup.filingmanager.address.find('ns1:stateorcountry') else ""}
        {f"<filingmanager_address_zipcode>{soup.filingmanager.address.find('ns1:zipcode').text.strip()}</filingmanager_address_zipcode>" if soup.filingmanager.address.find('ns1:zipcode') else ""}
    </filingmanager>
    """, 'xml'))
    soup.signatureblock.replace_with(BeautifulSoup(f"""
    <signatureblock>
        {f"<signatureblock_name>{soup.signatureblock.find('name').text.strip()}</signatureblock_name>" if soup.signatureblock.find('name') else ""}
        {f"<signatureblock_title>{soup.signatureblock.find('title').text.strip()}</signatureblock_title>" if soup.signatureblock.find('title') else ""}
        {f"<signatureblock_phone>{soup.signatureblock.find('phone').text.strip()}</signatureblock_phone>" if soup.signatureblock.find('phone') else ""}
        {f"<signatureblock_signature>{soup.signatureblock.find('signature').text.strip()}</signatureblock_signature>" if soup.signatureblock.find('signature') else ""}
        {f"<signatureblock_city>{soup.signatureblock.find('city').text.strip()}</signatureBlock_city>" if soup.signatureblock.find('city') else ""}
        {f"<signatureblock_stateorcountry>{soup.signatureblock.find('stateorcountry').text.strip()}</signatureblock_stateorcountry>" if soup.signatureblock.find('stateorcountry') else ""}
        {f"<signatureblock_signaturedate>{soup.signatureblock.find('signaturedate').text.strip()}</signatureblock_signaturedate>" if soup.signatureblock.find('signaturedate') else ""}
    </signatureblock>
    """, 'xml'))

    # Find all XML tags that have text but no children, and add their names to headers array if they don't already exist
    for tag in soup.findAll(lambda element: element.text.strip() is not None and not element.findAll()):
        if tag.name not in headers:
            headers.append(tag.name)
        new_fund[tag.name] = tag.text.strip()

    # Check if the new document should replace an existing one or be appended
    for n, fund in enumerate(existing_funds):
        if 'filingmanager_name' in fund and fund['filingmanager_name'] == new_fund['filingmanager_name']:
            logging.info('Fund already exists. Checking if this is a new version...')
            if 'reportcalendarorquarter' in fund and fund['reportcalendarorquarter'] == new_fund['reportcalendarorquarter']:
                # This is a duplicate and should be overwritten
                existing_funds[n] = new_fund
                found_existing = True

    # If the entry hasn't replaced an existing one, append it the array of existing funds
    if not found_existing:
        logging.info('New Fund, Appending to Existing...')
        existing_funds.append(new_fund)

    # Sort the headers to make it more orderly
    headers.sort()

    # Write the headers and entries to a search_summary.tsv file
    try:
        with open("./13F_Reports/search_summary.tsv", "wt") as tsv_file:
            tsv_writer = csv.writer(tsv_file, delimiter='\t')
            tsv_writer.writerow(headers)
            for fund in existing_funds:
                # Use row_builder to assemble each tsv line with the appropriate value or placeholder N/A
                row_builder = []
                for header in headers:
                    if header in fund:
                        row_builder.append(fund[header])
                    else:
                        row_builder.append('N/A')
                tsv_writer.writerow(row_builder)
    except IOError:
        logging.debug('Failed to open ./13F_Reports/search_summary.tsv')
