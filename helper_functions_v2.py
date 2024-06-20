from pprint import pprint
import random
from time import sleep
from parsel import Selector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from selenium.webdriver.common.action_chains import ActionChains
import os
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from telegram import Bot
from datetime import datetime
import pytz
import re
from bs4 import BeautifulSoup


# from mapwise import MapWiseScraper


# helper function for getting values from selector object
def parse(
        response: Selector,
        xpath: str,
        get_method: str = "get",
        comma_join: bool = False,
        space_join: bool = True,
):
    """_This function is used to get values from selector object by using xpath expressions_

    Args:
        response (_scrapy.Selector_): _A selector object on which we can use xpath expressions_
        xpath_str (_str_): _xpath expression to be used_
        get_method (str, optional): _whether to get first element or all elements_. Defaults to "get".
        comma_join (bool, optional): _if we are getting all elements whether to join on comma or not_. Defaults to False.
        space_join (bool, optional): _if we are getting all elements whether to join on space or not_. Defaults to False.

    Returns:
        _str_: _resultant value of using xpath expression on the scrapy.Selector object_
    """
    value = ""
    if get_method == "get":
        value = response.xpath(xpath).get()
        value = str((value or "")).strip()
    elif get_method == "getall":
        value = response.xpath(xpath).getall()
        if value:
            if comma_join:
                value = " ".join(
                    ", ".join([str(x).strip() for x in value]).split()
                ).strip()
                value = (value or "").strip()
            elif space_join:
                value = " ".join(
                    " ".join([str(x).strip() for x in value]).split()
                ).strip()
                value = (value or "").strip()
        else:
            value = ""
    return value


# this function is used to setup the bot
def bot_setup(headless: bool = False):
    """_This function is used to setup the bot_

    Args:
        headless (bool, optional): _whether to run the bot in headless mode or not_. Defaults to False.

    Returns:
        _selenium.webdriver_: _returns a selenium.webdriver object to be used_
    """
    user_agents = [
        # Add your list of user agents here
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    ]

    # select random user agent
    user_agent = random.choice(user_agents)

    # options to be used
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # options.add_argument('--blink-settings=imagesEnabled=false')
    # pass in selected user agent as an argument
    options.add_argument(f'user-agent={user_agent}')

    # Add additional options to avoid Cloudflare detection
    options.add_argument("--disable-web-security")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # if headless==True, make the bot headless
    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=Service(),
        options=options,
    )
    # setup implicit wait
    driver.implicitly_wait(3)
    driver.maximize_window()
    return driver


def get_urls_from_file():
    """Read the URLs from input file and return them as a dictionary."""
    # Get the input file path
    input_file_path = os.path.join(os.getcwd(), "gil_test.xlsx")

    try:
        # Read the input file
        df = pd.read_excel(input_file_path)
        # Check if "URL" and "mapwise" columns exist
        if "URL" not in df.columns or "mapwise" not in df.columns:
            raise KeyError("URL or mapwise column not found in input_v3.1.1.xlsx")

        # Modify the URLs and store them in a dictionary
        urls_dict = {}
        for index, row in df.iterrows():
            original_url = row["URL"].strip()
            modified_url = original_url.rstrip('/')
            formatted_url = modified_url.split("?")[0] + "?zaction=USER&zmethod=CALENDAR"
            urls_dict[original_url] = {"modified_url": formatted_url, "mapwise": row["mapwise"]}

        pprint(urls_dict)
        return urls_dict

    except FileNotFoundError:
        print("input_v3.1.1.xlsx file not found")
        exit()
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def get_foreclosure_dates_from_calendar(driver: webdriver):
    """_get foreclosure dates from calendar with pagination_

    Args:
        driver (_selenium.webdriver_): _webdriver_

    Returns:
        _list_: list of foreclosure dates_
    """
    # for pagination
    page_no = 1
    # list to store foreclosure dates
    foreclosure_dates = []

    # count to check if there is no data for 2 pages
    no_data_for_pages = 0

    # loop to get foreclosure dates from calendar
    while True:
        try:
            # wait for the calendar to load
            wait_for_element(
                driver, xpath='//div[@class="CALDAYBOX"]/div[@dayid]', wait_time=1
            )
            no_data_for_pages = 0
        except:  # if calendar not found
            # if calendar not found, increment the count
            no_data_for_pages += 1
            # if no data for 2 pages, break the loop
            if no_data_for_pages == 2:
                break

        # get the foreclosure dates from the calendar
        calendar_foreclosure_path = '//div[@class="CALDAYBOX"]/div[@dayid]//span[@class="CALACT" and not(text()="0")]/ancestor::div[@dayid]'
        temp_foreclosure_dates = get_attributes_list(
            driver, calendar_foreclosure_path, "dayid"
        )
        foreclosure_dates.extend(temp_foreclosure_dates)

        page_no += 1

        # click on next page
        try:
            click_btn(driver, xpath='(//a[contains(text(), "> >")])[1]')
            sleep(2)
        except Exception as e:
            break

    # pprint(foreclosure_dates)
    # return the foreclosure dates
    return foreclosure_dates


def generate_auction_link(domain_name: str, foreclosure_date: str):
    """_generate auction link_

    Args:
        domain_name (_str_): _domain name_
        foreclosure_date (_str_): _foreclosure data_

    Returns:
        _str_: _auction link_
    """
    auction_link = (
            "https://"
            + domain_name
            + "/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE="
            + foreclosure_date
    )
    return auction_link


def get_attributes_list(driver: webdriver, xpath: str, attribute_name: str):
    """_get the attributes of elements_

    Args:
        driver (webdriver): _webdriver_
        xpath (str): _xpath of elements_
        attribute_name (str): _attribute name of element_

    Returns:
        _list_: _list of attributes_
    """
    try:  # get the attributes of elements
        elements = driver.find_elements(By.XPATH, xpath)
        attributes = [ele.get_attribute(attribute_name) for ele in elements]
        return attributes
    except:
        return []


def get_orange_items(auc_row: Selector, foreclosure_date: str, auction_link: str, county):
    # get the auction items
    items = {}
    # api key
    items["api_key"] = "3BABE16B9C7C9BBD"

    items["property_address"] = ""
    items["property_street"] = ""
    items["property_state"] = ""
    items["property_city"] = ""
    items["property_zip"] = ""

    items["case_number"] = parse(
        auc_row,
        './/div[@class="AD_LBL" and text()="Case #:"]/following-sibling::div[@class="AD_DTA"]//text()',
    )

    # items = dict(sorted(items.items()))

    # get the auction status
    items["auction_status"] = parse(
        auc_row, './/div[@class="ASTAT_MSGB Astat_DATA"]/text()'
    )

    # get the sale amount
    items["sale_amount"] = parse(
        auc_row, './/div[contains(@class,"ASTAT_MSGD Astat_DATA")]/text()'
    )

    # get the auction state
    items["auction_state"] = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Auction Type:"]/following-sibling::td[@class="AD_DTA"]/text()',
    )

    # format the auction status
    if items["auction_state"] == "FORECLOSURE":
        items["auction_state"] = "Foreclosure"
    elif items["auction_state"] == "TAXDEED":
        items["auction_state"] = "Tax Deed"

    # get the sold to
    items["sold_to"] = parse(
        auc_row, './/div[contains(@class,"ASTAT_MSG_SOLDTO_MSG Astat_DATA")]/text()'
    )

    items["current_address"] = ""
    items["full_name"] = ""
    items["first_name"] = ""
    items["last_name"] = ""
    items["alternate_defendant_1"] = ""
    items["alternate_defendant_2"] = ""

    items["grantor"] = ""

    items["auction_link"] = auction_link

    # get the auction date
    items["auction_date"] = foreclosure_date

    # Find and extract the Parcel ID and URL
    parcel_id_element = auc_row.xpath(
        './/div[contains(text(), "Parcel ID:")]/following-sibling::div/a')
    parcel_id = parcel_id_element.xpath(
        './/text()').get().strip()  # Get the text content and strip whitespace

    parcel_id_url = parcel_id_element.attrib['href']  # Get the href attribute

    # Find and extract the final judgment amount
    final_judgment_amount = auc_row.xpath(
        './/div[contains(text(), "Final Judgment Amount:")]/following-sibling::div'
    ).xpath('.//text()').get().strip()

    items['final_judgment_amount'] = final_judgment_amount

    items['parcel_id'] = parcel_id

    # Find and extract the property address
    property_address_1 = auc_row.xpath(
        './/div[contains(text(), "Property Address:")]/following-sibling::div'
    ).xpath('.//text()').get().strip()

    property_address_2 = auc_row.xpath(
        './/div[contains(text(), "Property Address:")]/following-sibling::div/following-sibling::div'
    ).xpath('.//text()').get().strip()

    # if both parts of property address are available
    if property_address_1 and property_address_2:
        items["property_address"] = property_address_1 + " " + property_address_2
        items["property_street"] = property_address_1
        items["property_city"] = property_address_2.split(",")[0].strip()
        items["property_state"] = (
            property_address_2.split(",")[-1].strip().split("-")[0].strip()
        )
        if "-" in str(property_address_2).lower():
            items["property_zip"] = property_address_2.split("-")[-1].strip()
        else:
            items["property_zip"] = property_address_2.split(",")[-1].strip()

    # if only part 1 of property address is available
    if property_address_1 and not property_address_2:
        if "," in property_address_1 and "-" in property_address_1:
            items["property_address"] = property_address_1
            items["property_street"] = ""
            items["property_city"] = property_address_1.split(",")[0].strip()
            items["property_state"] = (
                property_address_1.split(",")[-1].strip().split("-")[0].strip()
            )
            if "-" in str(property_address_1).lower():
                items["property_zip"] = property_address_1.split("-")[-1].strip()
            else:
                items["property_zip"] = property_address_1.split(",")[-1].strip()
                items["property_state"] = "FL"
        else:
            items["property_address"] = property_address_1
            items["property_street"] = ""
            items["property_city"] = ""
            items["property_state"] = ""
            items["property_zip"] = ""

    # Find and extract the assessed value
    assessed_value = auc_row.xpath(
        './/div[contains(text(), "Assessed Value:")]/following-sibling::div'
    ).xpath('.//text()').get().strip()

    items['assessed_value'] = assessed_value

    # format the items to be sent
    items_to_send = {}
    for k, v in items.items():
        if v and str(v).strip():
            items_to_send[k] = str(v).strip()
        else:
            items_to_send[k] = ""

    # items_to_send = dict(sorted(items_to_send.items()))

    return items_to_send, parcel_id_url


def get_items(auc_row: Selector, foreclosure_date: str, auction_link: str, county):
    """_gets the auction items for each auction_

    Args:
        auc_row (Selector): _selector object to query with xpath and get data_
        foreclosure_date (str): _foreclosure date_
        auction_link (str): _auction link_

    Returns:
        _dict_: _dict of auction items_
    """

    # get the auction items
    items = {}
    # api key
    items["api_key"] = "3BABE16B9C7C9BBD"

    # get the property address
    # get part 1 of property address
    property_address_1 = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Property Address:"]/following-sibling::td[@class="AD_DTA"]/text()',
    )
    # get part 2 of property address
    property_address_2 = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Property Address:"]/following::tr[1]/th[not(text())]/following-sibling::td[1]/text()',
    )

    items["property_address"] = ""
    items["property_street"] = ""
    items["property_state"] = ""
    items["property_city"] = ""
    items["property_zip"] = ""

    # if both parts of property address are available
    if property_address_1 and property_address_2:
        items["property_address"] = property_address_1 + " " + property_address_2
        items["property_street"] = property_address_1
        items["property_city"] = property_address_2.split(",")[0].strip()
        items["property_state"] = (
            property_address_2.split(",")[-1].strip().split("-")[0].strip()
        )

        if items['property_state'].isdigit():
            items["property_state"] = "FL"

        if "-" in str(property_address_2).lower():
            items["property_zip"] = property_address_2.split("-")[-1].strip()
        else:
            items["property_zip"] = property_address_2.split(",")[-1].strip()

    # if only part 1 of property address is available
    if property_address_1 and not property_address_2:
        if "," in property_address_1 and "-" in property_address_1:
            items["property_address"] = property_address_1
            items["property_street"] = ""
            items["property_city"] = property_address_1.split(",")[0].strip()
            items["property_state"] = (
                property_address_1.split(",")[-1].strip().split("-")[0].strip()
            )
            if "-" in str(property_address_1).lower():
                items["property_zip"] = property_address_1.split("-")[-1].strip()
            else:
                items["property_zip"] = property_address_1.split(",")[-1].strip()
                items["property_state"] = "FL"
        else:
            items["property_address"] = property_address_1
            items["property_street"] = ""
            items["property_city"] = ""
            items["property_state"] = ""
            items["property_zip"] = ""

    # get the case number
    items["case_number"] = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Case #:"]/following-sibling::td[@class="AD_DTA"]//text()',
        get_method="getall",
    )

    # get the auction status
    items["auction_status"] = parse(
        auc_row, './/div[@class="ASTAT_MSGB Astat_DATA"]/text()'
    )

    # get the sale amount
    items["sale_amount"] = parse(
        auc_row, './/div[contains(@class,"ASTAT_MSGD Astat_DATA")]/text()'
    )

    # get the auction state
    items["auction_state"] = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Auction Type:"]/following-sibling::td[@class="AD_DTA"]/text()',
    )

    # format the auction status
    if items["auction_state"] == "FORECLOSURE":
        items["auction_state"] = "Foreclosure"
    elif items["auction_state"] == "TAXDEED":
        items["auction_state"] = "Tax Deed"

    # get the sold to
    items["sold_to"] = parse(
        auc_row, './/div[contains(@class,"ASTAT_MSG_SOLDTO_MSG Astat_DATA")]/text()'
    )

    #
    items["current_address"] = ""
    items["full_name"] = ""
    items["first_name"] = ""
    items["last_name"] = ""
    items["alternate_defendant_1"] = ""
    items["alternate_defendant_2"] = ""

    # get parcel id url
    parcel_id_url = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Parcel ID:"]/following-sibling::td[@class="AD_DTA"]/a/@href',
    )
    # take alternate key url instead of parcel id for citrus.realtaxdeed.com
    if "citrus.realtaxdeed.com" in auction_link:
        parcel_id_url = parse(
            auc_row,
            './/th[@class="AD_LBL" and text()="Alternate Key:"]/following-sibling::td[@class="AD_DTA"]/a/@href',
        )

        print(f"Parcel_id_url: {parcel_id_url}")

    items["grantor"] = ""
    items["auction_link"] = auction_link

    # items = dict(sorted(items.items()))

    # get the auction date
    items["auction_date"] = foreclosure_date

    # if opening bid is not available then use final judgment amount
    items["final_judgment_amount"] = parse(
        auc_row,
        './/th[@class="AD_LBL" and (text()="Opening Bid:" or text()="Final Judgment Amount:")]/following-sibling::td[@class="AD_DTA"]/text()',
    )
    try:
        # Convert to float to compare with assessment value
        final_judgment_amount_to_compare = float(re.sub(r'[^\d.]', '', items["final_judgment_amount"]))

        print(f"Final Judgment Value: {final_judgment_amount_to_compare}")
    except Exception as e:
        print(f"Error occurred while finding final judgment amount: {e}")

    # get the parcel id
    items["parcel_id"] = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Parcel ID:"]/following-sibling::td[@class="AD_DTA"]//text()',
        get_method="getall",
    )

    print(f'Parcel ID: {items["parcel_id"]}')

    # Get the assessed value
    items["assessed_value"] = parse(
        auc_row,
        './/th[@class="AD_LBL" and text()="Assessed Value:"]/following-sibling::td[@class="AD_DTA"]/text()',
    )

    print(f'Assessment Value IS => {items["assessed_value"]}')

    if items["assessed_value"]:
        try:
            # Convert to float to compare with Judgement value
            final_assesment_amount_to_compare = float(re.sub(r'[^\d.]', '', items["assessed_value"]))

            print(f"Final Assessment Value: {final_assesment_amount_to_compare}")

            # check_mapwise(
            #     final_assesment_amount_to_compare,
            #     final_judgment_amount_to_compare,
            #     items,
            #     driver
            # ) if mapwise else print("Data Already Updated with mapwise")

        except Exception as e:
            print(f"Error occurred while finding assessment value: {e}")

    # format the items to be sent
    items_to_send = {}
    for k, v in items.items():
        if v and str(v).strip():
            items_to_send[k] = str(v).strip()
        else:
            items_to_send[k] = ""

    # items_to_send = dict(sorted(items_to_send.items()))

    return items_to_send, parcel_id_url


from mapwise import map_main


def check_mapwise(row, driver, fault_status=False):
    # try:
    get_address_status = True
    assessment_amount = None  # Initialize as None
    if pd.notnull(row['assessed_value']):
        assessment_amount = float(row['assessed_value'])  # Convert to float

    judgment_amount = row['final_judgment_amount']
    property_street = row['property_street']
    parcel_id = row['parcel_id']
    owner_name = row['full_name']
    owner_address = row['current_address']

    if (
            owner_address.lower() != "nan" and owner_name.lower() != "nan"
    ):
        get_address_status = False
        print("Get Address Is False Now!!!")

    # if "https://citrus.realtaxdeed.com/" in auction_link__:
    #     print(f"Auction link => {auction_link__} => Continuing...")
    #     return row_str

    if str(assessment_amount).lower() != "nan" and str(
            judgment_amount).lower() != "nan":
        judgment_amount = float(judgment_amount.replace('$', '').replace(',', ''))
        if assessment_amount < judgment_amount:
            # if (
            #         row['current_address'].lower() != "nan" and row['full_name'].lower() != "nan"
            # ):
            print(
                f"(In MapWise nested if) Current Address => {row['current_address']} and Full Name => {row['full_name']}"
            )
            print(f"Assessment Amount ({assessment_amount}) < Judgement Amount ({judgment_amount})")
            row = map_main(driver, row, val=True, get_address=get_address_status)
            if get_address_status:
                defendants = []

                try:
                    if row['full_name'] is not None:
                        owner_name_parts = re.split(r'&|AND', row['full_name'], flags=re.IGNORECASE)
                        if len(owner_name_parts) >= 2:
                            for part in owner_name_parts:
                                # Split each part by '&'
                                split_ = part.split(" ")
                                print(f"Part => {split_}")
                                defendants.extend(split_)
                                # last_name, first_name = owner_name_parts
                                # print(f"Owner Name: {last_name}, {first_name}")

                            print(f"Defendants length => {len(defendants)}")
                            if len(defendants) >= 3:
                                row['full_name'] = defendants[0]
                                row['alternate_defendant_1'] = defendants[1]
                                row['alternate_defendant_2'] = defendants[2]
                                print(
                                    f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                )
                                row['first_name'] = "nan"
                                row['last_name'] = "nan"
                except Exception as e:
                    print(f"Error occurred while finding owner name parts: {e}")
                    owner_name_parts = row['full_name'].split(",")
                    if owner_name_parts >= 2:
                        row['last_name'], row['first_name'] = owner_name_parts
            else:
                print("Owner Information Already Filled!!!")

            return row
        elif assessment_amount > judgment_amount:
            print(
                f"(In MapWise nested Elif Condition) Assessment Amount ({assessment_amount}) > Judgement Amount ({judgment_amount})"
            )
            # if (
            #         row['current_address'].lower() != "nan" and row['full_name'].lower() != "nan"
            # ):
            if not get_address_status:
                print(f"(In MapWise nested Elif Condition) Address already filled...")
            if get_address_status:
                print(
                    f"(In MapWise nested Elif Condition) Address NOT filled... Address | {owner_address} | Name => {owner_name}")
                row = map_main(driver, row, val=True, get_address=get_address_status)
                defendants = []
                try:
                    if row['full_name'] is not None:
                        owner_name_parts = re.split(r'&|AND', row['full_name'], flags=re.IGNORECASE)
                        if len(owner_name_parts) >= 2:
                            for part in owner_name_parts:
                                # Split each part by '&'
                                split_ = part.split(" ")
                                print(f"Part => {split_}")
                                defendants.extend(split_)
                                # last_name, first_name = owner_name_parts
                                # print(f"Owner Name: {last_name}, {first_name}")

                            print(f"Defendants length => {len(defendants)}")
                            if len(defendants) >= 3:
                                row['full_name'] = defendants[0]
                                row['alternate_defendant_1'] = defendants[1]
                                row['alternate_defendant_2'] = defendants[2]
                                print(
                                    f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                )
                                row['first_name'] = "nan"
                                row['last_name'] = "nan"
                except Exception as e:
                    print(f"Error occurred while finding owner name parts: {e}")
                    owner_name_parts = row['full_name'].split(",")
                    if owner_name_parts >= 2:
                        row['last_name'], row['first_name'] = owner_name_parts
            else:
                print("Owner Information Already Filled!!!")
            return row

    elif (
            pd.isnull(str(assessment_amount).lower()) or str(assessment_amount).lower() in ("nan", "")
    ) and fault_status:
        print(f"I Think its Faulty... Assessment amount => {assessment_amount}")
        row = map_main(driver, row, get_address=get_address_status, get_assessment=True)
        if row is not None:
            print("Result:")
            # print("--------------------------------------------------------")
            # pprint(row)
            # print("--------------------------------------------------------")
            return row
    else:
        print("One or more of the required fields (assessment_amount, judgment_amount, property_street) is null.")
        return row
    # except Exception as e:
    #     print(f"Error occurred while processing MapWise data: {e}")
    #     return row


def click_btn(driver: webdriver, xpath: str, wait_time: int = 5):
    """_clicks an element_

    Args:
        driver (webdriver): _webdriver_
        xpath (str): _xpath of element to be clicked_
        wait_time (int, optional): _seconds to wait for element to be present_. Defaults to 5.
    """
    # wait for the element to be present
    btn = WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    # move to the element
    ActionChains(driver).move_to_element(btn).perform()
    sleep(1)
    # click the element
    ActionChains(driver).click(btn).perform()
    return


def wait_for_element(driver: webdriver, xpath: str, wait_time: int = 5):
    """_wait for an element_

    Args:
        driver (webdriver): _webdriver_
        xpath (str): _xpath of element to be clicked_
        wait_time (int, optional): _seconds to wait for element to be present_. Defaults to 5.
    """
    # wait for the element to be present
    WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    return


def wait_for_loading(driver: webdriver):
    """_wait for the spinning loading to disappear_

    Args:
        driver (webdriver): _webdriver_
    """
    # flag to check if loading is still present
    is_loading_animation = True
    # loop to wait for loading to disappear
    while True:
        for _ in range(5):
            # get the page source
            response = Selector(text=driver.page_source)
            # check if loading is present
            loading_animation = parse(
                response, '//div[contains(@class,"Loading") or contains(@class,"Wait")]'
            )
            # if loading is present, wait for 1 second
            if loading_animation:
                sleep(1)
                continue
            else:  # if loading is not present, break the loop
                is_loading_animation = False
                break
        else:  # if loading is still present, refresh the page
            driver.refresh()
            continue

        # if loading is not present, break the loop
        if not is_loading_animation:
            break


def send_to_google_sheets(data):
    """
    Sends a list of dictionaries to a Google Sheet.

    Parameters:
    - data: List of dictionaries to be sent to Google Sheet.

    Note: You need to set up the Google Sheets API and obtain credentials before using this function.
    """
    # Set up credentials
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    # get the credentials from the json file
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "googlesheetcreds.json", scope
    )
    # authorize the credentials
    gc = gspread.authorize(credentials)

    # Open the Google Spreadsheet by name
    spreadsheet_name = "Sheet for Bot 1 and Bot 2"
    spreadsheet = gc.open(spreadsheet_name)

    # Select the worksheet by name
    worksheet_name = "Bot 1 Output"
    worksheet = spreadsheet.worksheet(worksheet_name)
    # Extract the header row from the data
    header = list(data[0].keys())

    # Check if the worksheet is empty
    if worksheet.row_count == 0:
        while True:
            # If the worksheet is empty, add the header row
            try:
                worksheet.append_row(header)
                break
            except:
                sleep(30)

    # Extract and append data rows to the worksheet
    for entry in data:
        while True:
            try:
                row_data = [entry[column] for column in header]
                worksheet.append_row(row_data)
                break
            except:
                sleep(30)

    return


def send_message_to_telegram(message: str):
    """_send the message to telegram_

    Args:
        message (str): _string message to be sent_
    """
    # Replace 'YOUR_TOKEN' with the token provided by BotFather
    TOKEN = "6430312414:AAHy9wOVNsmCIuWi1wPXJFGzZxlqlYsCGzo"

    # Replace 'YOUR_CHAT_ID' with the chat ID where you want to send the message
    CHAT_ID = "-4065717745"

    # Create the bot
    bot = Bot(token=TOKEN)

    # Send the message
    bot.send_message(chat_id=CHAT_ID, text=message)


def get_current_time_in_est_12hr_format():
    """_get current time in EST 12 hour format_

    Returns:
        _str_: _formatted time in EST 12 hour format_
    """
    # Set the time zone to Eastern Standard Time (EST)
    est_timezone = pytz.timezone("US/Eastern")

    # Get the current time in UTC
    utc_now = datetime.utcnow()

    # Convert UTC time to EST
    est_now = utc_now.replace(tzinfo=pytz.utc).astimezone(est_timezone)

    # Format the time in 12-hour format with AM/PM
    formatted_time = est_now.strftime("%d-%m-%Y %I:%M %p")

    return formatted_time


def get_owner_info(
        driver: webdriver, domain: str, parcel_id_url: str, auction_items: dict
):
    """_
    depending on the domain call the respective function to get the
    name and address of the owner of the property
    _

    Args:
        driver (webdriver): _webdriver_
        domain (str): _domain name_
        parcel_id_url (str): _parcel id url_
        auction_items (dict): _dict containing auction items_

    Returns:
        _dict_: _auction items with the names and address of owner_
    """
    if domain == "brevard.realforeclose.com":
        auction_items = get_owner_info_brevard_realforeclose(
            driver, parcel_id_url, auction_items
        )

    elif domain == "broward.realforeclose.com":
        auction_items = get_owner_info_broward_realforeclose(
            driver, parcel_id_url, auction_items
        )

    elif domain == "charlotte.realforeclose.com":
        auction_items = get_owner_info_charlotte_realforeclose(
            driver, parcel_id_url, auction_items
        )

    elif domain == "citrus.realtaxdeed.com":
        auction_items = get_owner_info_citrus_taxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "duval.realforeclose.com" or domain == "duval.realtaxdeed.com":
        # Checking this right now (26-mar-24 10:16pm PST)
        auction_items = get_owner_info_duval_realforeclose_taxdeed(
            driver, parcel_id_url, auction_items
        )

    elif domain == "escambia.realforeclose.com" or domain == "escambia.realtaxdeed.com":
        auction_items = get_owner_info_escambia_realforeclose_and_taxdeed(
            driver, parcel_id_url, auction_items
        )

    elif domain == "hillsborough.realforeclose.com":
        auction_items = get_owner_info_hissbourough_realforeclose(
            driver, parcel_id_url, auction_items
        )
    elif domain == "hillsborough.realtaxdeed.com":
        auction_items = get_owner_infor_hissbourough_realtaxdeed(
            driver, parcel_id_url, auction_items
        )

    elif domain == "lee.realforeclose.com" or domain == "lee.realtaxdeed.com":
        auction_items = get_owner_info_lee_realforeclose_and_taxdeed(
            driver, parcel_id_url, auction_items
        )

    elif domain == "miamidade.realforeclose.com":
        auction_items = get_owner_info_miamidade_realforeclose(
            driver, parcel_id_url, auction_items
        )
    elif (
            domain == "palmbeach.realforeclose.com" or domain == "palmbeach.realtaxdeed.com"
    ):
        print("Processing palm beach urls...")
        auction_items = get_owner_info_palmbeach_realforeclose_and_taxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "pasco.realforeclose.com" or domain == "pasco.realtaxdeed.com":
        auction_items = get_owner_info_pasco_realforeclose_taxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "polk.realforeclose.com" or domain == "polk.realtaxdeed.com":
        auction_items = get_owner_info_polk_realforeclose_and_taxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "putnam.realtaxdeed.com":
        auction_items = get_owner_info_putnam_realtaxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "volusia.realforeclose.com":
        auction_items = get_owner_info_volusia_realforeclose(
            driver, parcel_id_url, auction_items
        )
    # CLOUDFLARE BLOCKAGE!!!
    # elif (
    #         domain == "gilchrist.realforeclose.com" or domain == "gilchrist.realtaxdeed.com"
    # ):
    #     print("Processing Gilchrist auction owner details...")
    #     auction_items = get_owner_info_gilchrist_realforeclose(
    #         driver, parcel_id_url, auction_items
    #     )
    elif domain == "lake.realtaxdeed.com":
        print("Processing lake auction owner details...")
        auction_items = get_owner_info_lake_realtaxdeed(
            driver, parcel_id_url, auction_items
        )
    # CLOUDFLARE BLOCKAGE!!!
    # elif domain == "alachua.realtaxdeed.com":
    #     print("Processing Alachua auction owner details...")
    #     auction_items = get_owner_info_alachua_realtaxdeed(
    #         driver, parcel_id_url, auction_items
    #     )
    elif domain == "baker.realtaxdeed.com":
        print("Processing Baker auction owner details...")
        auction_items = get_owner_info_baker_realtaxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "marion.realtaxdeed.com" or domain == "marion.realforeclose.com":
        print("Processing Marion auction owner details...")
        auction_items = get_owner_info_marion_realtaxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "martin.realforeclose.com" or domain == "martin.realtaxdeed.com":
        print("Processing Martin auction owner details...")
        auction_items = get_owner_info_martin_realforeclose_and_taxdeed(
            driver, parcel_id_url, auction_items
        )
    elif domain == "orange.realtaxdeed.com":
        print("Processing Orange auction owner details...")
        auction_items = get_owner_info_orange_realtaxdeed(
            driver, parcel_id_url, auction_items
        )
    # orange county has a very different structure
    elif domain == "myorangeclerk.realforeclose.com":
        auction_items = get_owner_info_orange_realforeclose(
            driver, parcel_id_url, auction_items
        )

    return auction_items


def get_owner_info_orange_realtaxdeed(
        driver, parcel_id_url, auction_items
):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    
    try:
        # Wait for the general info section to be visible
        property_owner = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(text(), 'Name(s):')]/.."))
        ).text.strip()

        sleep(1.5)

        print(f"Property Owner => {property_owner}")
        auction_items['full_name'] = property_owner

        property_owners = property_owner.replace('Name(s):', '').split('\n')
        property_owners = [owner for owner in property_owners if owner.strip()]

        if len(property_owners) == 1:
            auction_items['full_name'] = property_owners[0]
            print(f"Owner Name FINALLY = {property_owners[0]}")

        try:
            property_owners_fl = property_owner.split(',')
            auction_items['last_name'] = property_owners_fl[0]
            auction_items['first_name'] = property_owners_fl[1]
        except:
            print("Couldn't split it")
            auction_items['last_name'] = ''
            auction_items['first_name'] = ''

        if len(property_owners) == 2:
            auction_items['full_name'] = property_owners[0]
            print(f"Owner Name = {property_owners[0]}")
            auction_items['alternate_defendant_1'] = property_owners[1]
            print(f"Alt Def Name = {property_owners[1]}")

        if len(property_owners) >= 3:
            auction_items['full_name'] = property_owners[0]
            auction_items['alternate_defendant_1'] = property_owners[1]
            auction_items['alternate_defendant_2'] = property_owners[2]

        # Extract mailing address
        mailing_address = driver.find_element(By.XPATH,
                                            "//div[contains(span/text(), 'Mailing Address On File')]").text.strip().replace(
            'Mailing Address On File:', '').replace('Incorrect Mailing Address?', '').replace('\n', ' ')

        auction_items['current_address'] = mailing_address

        print("Property Owners:", property_owners)
        print("Mailing Address:", mailing_address)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_martin_realforeclose_and_taxdeed(
        driver, parcel_id_url, auction_items
):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        # Wait for the general info section to be visible
        general_info = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "table-section.general-info"))
        )

        # Extract property owners
        property_owner = general_info.find_element(By.XPATH,
                                                "//strong[text()='Property Owners']/..").text.strip().replace(
            'Property Owners', '')

        print(f"Property Owner => {property_owner}")
        auction_items['full_name'] = property_owner

        property_owners = property_owner.split('\n')
        property_owners = [owner for owner in property_owners if owner.strip()]
        if len(property_owners) == 1:
            auction_items['full_name'] = property_owners[0]
            print(f"Owner Name FINALLY = {property_owners[0]}")

        try:
            property_owners_fl = property_owner.split(',')
            auction_items['last_name'] = property_owners_fl[0]
            auction_items['first_name'] = property_owners_fl[1]
        except:
            print("Couldn't split it")

        if len(property_owners) == 2:
            auction_items['full_name'] = property_owners[0]
            print(f"Owner Name = {property_owners[0]}")
            auction_items['alternate_defendant_1'] = property_owners[1]
            print(f"Alt Def Name = {property_owners[1]}")

        if len(property_owners) >= 3:
            auction_items['full_name'] = property_owners[0]
            auction_items['alternate_defendant_1'] = property_owners[1]
            auction_items['alternate_defendant_2'] = property_owners[2]

        # Extract mailing address
        mailing_address = general_info.find_element(By.XPATH,
                                                    "//strong[text()='Mailing Address']/..").text.strip().replace(
            'Mailing Address', '').replace('\n', ' ')

        auction_items['current_address'] = mailing_address

        print("Property Owners:", property_owners)
        print("Mailing Address:", mailing_address)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_marion_realtaxdeed(
        driver, parcel_id_url, auction_items
):
    if parcel_id_url == "http://www.pa.marion.fl.us/PRC.aspx?key=&YR=2024&mName=False&mSitus=False":
        return auction_items
    
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        # Find the <td> element containing the owner information
        owner_info_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//center[a[contains(text(), 'Property Information')]]/following-sibling::table//td[1]"))
        )

        # Extract owner information
        owner_info_text = owner_info_element.text.strip()

        # Count the number of newline characters
        new_lines = owner_info_text.count('\n')
        
        # Set the info separator based on the number of newlines
        if new_lines == 3:
            info_separator = 2
        else:
            info_separator = 1

        print(f"Newline count: {new_lines}, Info separator: {info_separator}")

        # Split owner information into name and address parts
        owner_info_parts = owner_info_text.split('\n')
        owner_name = owner_info_parts[:info_separator][0]
        auction_items['full_name'] = owner_name
        if info_separator == 2:
            alternate_defendant = owner_info_parts[:info_separator][1].replace('  ', '')
            print(f"Alternate Defendant: '{alternate_defendant}'")
            auction_items['alternate_defendant_1'] = alternate_defendant
            
        owner_address = ' '.join(owner_info_parts[info_separator:]).replace('\n', ' ').strip()
        auction_items['current_address'] = owner_address

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_baker_realtaxdeed(
        driver, parcel_id_url, auction_items
):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        # Find the owner information section
        owner_info_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ownerinfo"))
        )

        # Extract owner name
        owner_name_element = owner_info_section.find_element(By.XPATH,
                                                            "//span[@class='subhead' and text()='Owner:']/following-sibling::div/span")
        owner_name = owner_name_element.text.strip()
        auction_items['full_name'] = owner_name

        try:
            owner_names = owner_name.split("&")
            auction_items['full_name'] = owner_names[0]
            auction_items['alternate_defendant_1'] = owner_names[1]
        except:
            print("Only 1 owner found")

        owner_names_fl = owner_name.split(',')
        auction_items['last_name'] = owner_names_fl[0]
        auction_items['first_name'] = owner_names_fl[1]

        # Extract mailing address
        mailing_address_element = owner_info_section.find_element(By.XPATH,
                                                                "//span[@class='subhead' and text()='Mailing Address:']/following-sibling::div/span")
        mailing_address = mailing_address_element.text.strip()
        print(f"Raw Mailing Address: {mailing_address}")
        mailing_address = mailing_address.replace('\n', '').replace('&nbsp;', ' ')
        print(f"Purified Mailing Address: {mailing_address}")

        auction_items['current_address'] = mailing_address

        # Print the extracted owner name and mailing address
        print("Owner Name:", owner_name)
        print("Mailing Address:", mailing_address)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_alachua_realtaxdeed(
        driver, parcel_id_url, auction_items
):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        owner_info_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sdw1-owners-ownerspace"))
        )

        owner_name = owner_info_div.find_element(By.ID,
                                                "ctlBodyPane_ctl03_ctl01_rptOwner_ctl00_sprOwnerName1_lnkUpmSearchLinkSuppressed_lblSearch").text.strip()
        # try:
        owner_name = owner_name.find_element(By.TAG_NAME, "a").text.strip()
        # except:
        #     print("no anchor found")

        print(f"Owner Name => {owner_name}")
        auction_items['full_name'] = owner_name
        # try:
        owner_names = owner_name.split("&")
        auction_items['full_name'] = owner_names[0]
        auction_items['alternate_defendant_1'] = owner_names[1]
        # except:
        #     print("Only 1 owner found")

        owner_names_fl = owner_name.split(',')
        auction_items['last_name'] = owner_names_fl[0]
        auction_items['first_name'] = owner_names_fl[1]

        owner_address = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctlBodyPane_ctl03_ctl01_rptOwner_ctl00_lblOwnerAddress"))
        ).text.strip()
        owner_address = owner_address.replace('\n', ' ').replace('  ', '')
        print(f"Owner address => {owner_address}")
        auction_items['current_address'] = owner_address

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_lake_realtaxdeed(
        driver, parcel_id_url, auction_items
):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        # Wait for the table element to be visible
        table = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "property_head"))
        )

        # Find elements using WebDriverWait and XPath
        name_element = table.find_element(By.XPATH,
                                        "//td[@class='property_field' and text()='Name:']/following-sibling::td[@class='property_item']")
        mailing_address_element = table.find_element(By.XPATH,
                                                    "//td[@class='property_field' and contains(text(), 'Mailing Address')]/following-sibling::td[@class='property_item']")
        parcel_number_element = table.find_element(By.XPATH,
                                                "//td[@class='property_field' and contains(text(), 'Parcel Number')]/following-sibling::td[@class='property_item']")

        assessed_div = driver.find_element(By.ID, "estTaxes")
        est_table = assessed_div.find_element(By.CLASS_NAME, 'property_data_table')
        # Get the outer HTML
        outer_html = est_table.get_attribute('outerHTML')
        pprint(outer_html)
        assessed_value = est_table.find_element(By.XPATH, ".//tr[@class='property_row']/td[3]")

        __assessed_value = assessed_value.text
        auction_items['assessed_value'] = __assessed_value
        name = name_element.text.strip()
        auction_items['full_name'] = name
        mailing_address = mailing_address_element.text.strip().replace("\n", " ")
        auction_items['current_address'] = mailing_address
        parcel_number = parcel_number_element.text.strip()
        auction_items['parcel_id'] = parcel_number

        # Print the extracted data
        print("Name:", name)
        print("Mailing Address:", mailing_address)
        print("Parcel Number:", parcel_number)
        print("First Assessed Value:", __assessed_value)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_gilchrist_realforeclose(
        driver, parcel_id_url, auction_items
):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        # Wait for the "Assessed Value" row to be visible
        row = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.XPATH, "//th[text()='Assessed Value']/parent::tr"))
        )
        # Find the td tag containing the value within the corresponding row
        value_td = row.find_element(By.CLASS_NAME, 'value-column')
        # Get the text inside the td tag
        assessed_value = value_td.text.strip()
        print(f"Asessed Value of Gilchrist => {assessed_value}")
        auction_items['assessed_value'] = assessed_value
    except Exception as e:
        print(f"Could not find assessed value of Gilchrist: {e}")

    try:
        # Wait for the span tag within the specific div to be visible
        span_tag = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH,
                                              "//div[@id='ctlBodyPane_ctl00_ctl01_dynamicSummary_rptrDynamicColumns_ctl00_pnlSingleValue']/span"))
        )
        # Get the text inside the span tag
        auction_items['parcel_id'] = span_tag.text.strip()
    except Exception as e:
        print(f"Could not find parcel id: {e}")

    try:
        # Wait for the owner name span tag to be visible
        owner_name_1 = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH,
                                              "//span[@id='ctlBodyPane_ctl01_ctl01_rptOwner_ctl00_sprOwnerName1_lnkUpmSearchLinkSuppressed_lblSearch']"))
        )
        # Get the text inside the span tag
        auction_items['full_name'] = owner_name_1.text.strip()
    except Exception as e:
        print(f"Could not find owner name: {e}")

    try:
        # Wait for the alternate defendant span tag to be visible
        alt_defendent_1 = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH,
                                              "//span[@id='ctlBodyPane_ctl01_ctl01_rptOwner_ctl00_sprOwnerName2_lnkUpmSearchLinkSuppressed_lblSearch']"))
        )
        auction_items['alternate_defendant_1'] = alt_defendent_1.text.strip()
    except Exception as e:
        print(f"Could not find alternative defendant name: {e}")

    try:
        # Wait for the owner address span tag to be visible
        owner_address = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[@id='ctlBodyPane_ctl01_ctl01_rptOwner_ctl00_lblOwnerAddress']"))
        )
        auction_items['current_address'] = owner_address.text.strip()
    except Exception as e:
        print(f"Could not find owner address: {e}")

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


# def get_owner_info_miamidade_realforeclose(
#         driver: webdriver, parcel_id_url, auction_items
# ):
#     driver.execute_script("window.open('', '_blank');")
#     driver.switch_to.window(driver.window_handles[1])
#     driver.get(parcel_id_url)
#     try:
#         wait_for_element(driver, xpath='//span[text()="Owner"]')
#     except Exception as e:
#         driver.close()
#         driver.switch_to.window(driver.window_handles[0])
#         return auction_items
#
#     response = Selector(text=driver.page_source)
#
#     owner_rows = response.xpath(
#         '//span[text()="Owner"]/parent::strong/following-sibling::div[1]/div'
#     )
#     for owner_row_idx, owner_row in enumerate(owner_rows):
#         owner_name = parse(owner_row, ".//text()", get_method="getall")
#
#         if owner_row_idx == 0:
#             auction_items["full_name"] = owner_name
#             first_name = owner_name.split()[0].strip()
#             if len(owner_name.split()) > 1:
#                 last_name = " ".join(owner_name.split()[1:]).strip()
#             else:
#                 last_name = ""
#
#             auction_items["first_name"] = first_name
#             auction_items["last_name"] = last_name
#
#         elif owner_row_idx == 1:
#             auction_items["alternate_defendant_1"] = owner_name
#         elif owner_row_idx == 2:
#             auction_items["alternate_defendant_2"] = owner_name
#
#     mailing_address = parse(
#         response,
#         '//span[text()="Mailing Address"]/parent::strong/following-sibling::div[1]//text()',
#         get_method="getall",
#     )
#     auction_items["current_address"] = mailing_address
#
#     driver.close()
#     driver.switch_to.window(driver.window_handles[0])
#
#     return auction_items

def get_owner_info_miamidade_realforeclose(
        driver: webdriver, parcel_id_url, auction_items
):
    if parcel_id_url == 'https://www.miamidade.gov/Apps/PA/propertysearch/#/?folio=':
        return auction_items

    # Open a new browser tab and navigate to the URL
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        # Wait for the "Owner" element to appear on the page
        wait_for_element(driver, xpath='//strong//span[text()="Owner"]')
    except Exception as e:
        # Close the new tab and return the auction items as is if the element is not found
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    # Parse the page source using Selector from Parsel
    response = Selector(text=driver.page_source)

    # Retrieve the owner's name and split by multiple delimiters
    owner_element = response.xpath('//span[text()="Owner"]/parent::*/following-sibling::*').xpath('string()').get()
    print(owner_element)
    if owner_element:
        # Split by '&', '|', 'AND', or '\n'
        owner_names = re.split(r'&|AND|\n', owner_element, flags=re.IGNORECASE)
        # Strip whitespaces and filter out empty strings from the split list
        owner_names = [name.strip() for name in owner_names if name.strip()]

        # Check if owner_names list has elements
        if owner_names:
            # Use the first owner name
            auction_items['full_name'] = owner_names[0]

            # Extract first and last names
            if ',' in owner_names[0]:
                names = owner_names[0].split(',')
                auction_items['first_name'] = names[1].strip()
                auction_items['last_name'] = names[0].strip()
            else:
                auction_items['last_name'] = ''
                auction_items['first_name'] = ''

            # Add alternate defendants if present
            if len(owner_names) > 1:
                auction_items['alternate_defendant_1'] = owner_names[1].strip()
            if len(owner_names) > 2:
                auction_items['alternate_defendant_2'] = owner_names[2].strip()

    # Retrieve the mailing address
    mailing_address = response.xpath('//span[text()="Mailing Address"]/parent::*/following-sibling::*').xpath(
        'string()').get()
    print(f"mailing_address =:> {mailing_address}")
    if mailing_address:
        auction_items['current_address'] = mailing_address

    # Retrieve the folio number
    parcel_id = response.xpath('//span[text()="Folio:"]/following-sibling::span/text()').get()
    print(f"parcel_id =:> {parcel_id}")
    if parcel_id:
        auction_items['parcel_id'] = parcel_id.strip()

    # Close the new tab and switch back to the original tab
    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    # Return the updated auction items dictionary
    return auction_items


def get_owner_info_broward_realforeclose(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    try:
        wait_for_element(
            driver,
            xpath='//span[@class="RedBodyCopyBold9" and contains(text(), "Property Owner")]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        xpath='//span[@class="RedBodyCopyBold9" and contains(text(), "Property Owner")]/following::td[1]/span/text()',
        get_method="getall",
        space_join=False,
    )
    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name.replace(",", "").strip()
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//span[@class="RedBodyCopyBold9" and contains(text(), "Mailing Address")]/parent::td/following-sibling::td[1]/span//text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    if not auction_items["assessed_value"]:
        auction_items["assessed_value"] = parse(
            response,
            xpath='//td[@align="center" and contains(., "Assessed /")]/parent::tr[1]/following-sibling::tr[2]/td[5]//text()',
            get_method="getall",
        )

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_infor_hissbourough_realtaxdeed(driver, parcel_id_url, auction_items):
    print(f"Parcel ID URL is seach!!! => {parcel_id_url}")
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "link.force-one-line"))
    ).click()

    try:
        wait_for_element(
            driver,
            xpath='//div[@id="details"]/h2',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        xpath='//h4[@data-bind="html: publicOwner()"]/text()',
        get_method="getall",
        space_join=False,
    )

    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//p[@data-bind="text: mailingAddress.publicAddress()"]/text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    assessment_value = parse(
        response,
        '//td[@data-bind="text: formattedAssessedVal"]'
    )



    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_hissbourough_realforeclose(driver, parcel_id_url, auction_items):
    if (
            parcel_id_url
            == "http://www.hcpafl.org/CamaDisplay.aspx?OutputMode=Display&SearchType=RealEstate&ParcelID="
    ):
        return auction_items

    else:
        driver.execute_script("window.open('', '_blank');")
        driver.switch_to.window(driver.window_handles[1])
        driver.get(parcel_id_url)
        try:
            wait_for_element(
                driver,
                xpath='//div[@id="details"]/h2',
            )
        except Exception as e:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return auction_items

        response = Selector(text=driver.page_source)
        owner_names = parse(
            response,
            xpath='//h4[@data-bind="html: publicOwner()"]/text()',
            get_method="getall",
            space_join=False,
        )

        owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

        for owner_name_idx, owner_name in enumerate(owner_names):
            if owner_name_idx == 0:
                auction_items["full_name"] = owner_name

                first_name = owner_name.split()[0].strip()
                if len(owner_name.split()) > 1:
                    last_name = " ".join(owner_name.split()[1:]).strip()
                else:
                    last_name = ""

                auction_items["first_name"] = first_name
                auction_items["last_name"] = last_name

            elif owner_name_idx == 1:
                auction_items["alternate_defendant_1"] = owner_name
            elif owner_name_idx == 2:
                auction_items["alternate_defendant_2"] = owner_name

        mailing_address = parse(
            response,
            '//p[@data-bind="text: mailingAddress.publicAddress()"]/text()',
            get_method="getall",
        )
        auction_items["current_address"] = mailing_address

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items


def get_owner_info_palmbeach_realforeclose_and_taxdeed(
        driver: webdriver, parcel_id_url, auction_items
):
    if (
            parcel_id_url
            == "https://www.pbcgov.com/papa/Asps/PropertyDetail/PropertyDetail.aspx?parcel="
    ):
        print("skipping")
        return auction_items

    if (
            parcel_id_url == "https://pbcpao.gov/Property/Details?parcelId=TIMESHARE"
    ):
        print("skipping")
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    # sleep(600)
    # try:
    #     wait_for_element(
    #         driver,
    #         xpath='//td[@class="TDLabelBoldBkgLeft" and text()="Owner(s)"]',
    #     )
    # except Exception as e:
    #     print("Exception occurred")
    #     driver.close()
    #     driver.switch_to.window(driver.window_handles[0])
    #     return auction_items

    # response = Selector(text=driver.page_source)
    # owner_names = parse(
    #     response,
    #     xpath='//td[@class="TDLabelBoldBkgLeft" and text()="Owner(s)"]/parent::tr/following-sibling::tr/td/text()',
    #     get_method="getall",
    #     space_join=False,
    # )

    try:
        print("Searching for table element")

        # Find all elements with class 'col-12 has-accordion'
        table_elements = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'col-12.has-accordion')))

        print("Printing table elements")
        for element in table_elements:
            # Extract header text
            header_text = element.find_element(By.TAG_NAME, 'h2').text.strip()

            # Extract owner information
            if header_text.lower() == "owner information":
                print(f"Header: {header_text}")
                table = element.find_element(By.CLASS_NAME, 'table_scroll')
                # Find the table rows containing owner names and addresses
                rows = table.find_elements(By.TAG_NAME, 'tr')
                for row in rows:
                    # Extract owner names and mailing address
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 2:
                        auction_items["full_name"] = cells[0].text.replace('\n', ' ').strip()
                        auction_items["current_address"] = cells[2].text.replace('\n',
                                                                                ' ').strip()  # Replace newline with space

                        # Print owner names and formatted mailing address
                        print(f'Owner(s): {auction_items["full_name"]}')
                        print(f'Mailing Address: {auction_items["current_address"]}')

            if header_text.lower() == "assessed & taxable values":
                print(f"Header: {header_text}")
                table = element.find_element(By.CLASS_NAME, 'table_scroll')
                # Find the table rows containing owner names and addresses
                rows = table.find_elements(By.TAG_NAME, 'tr')

                for row in rows:
                    auction_items["assessed_value"] = row.find_elements(By.CLASS_NAME, "text-right")[0].text.strip()
                    # print(f'Assessed Value: {auction_items["assessed_value"]}')

                # Split owner information into lines
                # lines = owner_info.split('\n')
                # # First line contains the owner's name
                # owner_name = lines[1]
                # # Second line contains the mailing address
                # mailing_address_1 = lines[2]
                # mailing_address_2 = lines[3]
                # mailing_address = mailing_address_1 + " " + mailing_address_2

                # print("Owner Name:", owner_name)
                # print("Mailing Address:", mailing_address)

        # owner_names = [x.strip() for x in owner_names if x and str(x).strip()]
        #
        # for owner_name_idx, owner_name in enumerate(owner_names):
        #     if owner_name_idx == 0:
        #         auction_items["full_name"] = owner_name
        #
        #         first_name = owner_name.split()[0].strip()
        #         if len(owner_name.split()) > 1:
        #             last_name = " ".join(owner_name.split()[1:]).strip()
        #         else:
        #             last_name = ""
        #
        #         auction_items["first_name"] = first_name
        #         auction_items["last_name"] = last_name
        #
        #     elif owner_name_idx == 1:
        #         auction_items["alternate_defendant_1"] = owner_name
        #     elif owner_name_idx == 2:
        #         auction_items["alternate_defendant_2"] = owner_name
        #
        # mailing_address = parse(
        #     response,
        #     '//span[contains(@id,"MainContent_lblAddrLine")]//text()',
        #     get_method="getall",
        # )
        # auction_items["current_address"] = mailing_address
        #
        # if not auction_items["assessed_value"]:
        #     auction_items["assessed_value"] = parse(
        #         response,
        #         xpath='//span[@id="MainContent_lblAssessedValue1"]/text()',
        #     )

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_polk_realforeclose_and_taxdeed(driver, parcel_id_url, auction_items):
    if (
            parcel_id_url
            == "http://www.polkpa.org/CamaDisplay.aspx?OutputMode=Display&SearchType=RealEstate&Page=FindByID&ParcelID="
    ):
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    try:
        wait_for_element(
            driver,
            xpath='//h4[contains(text(), "Owners")]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        xpath='//h4[contains(text(), "Owners")]/following-sibling::table[1]/tbody/tr/td[1]/text()',
        get_method="getall",
        space_join=False,
    )

    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//h4[contains(text(), "Mailing Address")]/following-sibling::table[1]/tbody/tr/td[2]/span/text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_duval_realforeclose_taxdeed(driver, parcel_id_url, auction_items):
    if parcel_id_url == "https://paopropertysearch.coj.net/Basic/Detail.aspx?RE=":
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    try:
        wait_for_element(
            driver,
            xpath='//div[@id="ownerName"]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        xpath='//div[@id="ownerName"]/h2/span/text()',
        get_method="getall",
        space_join=False,
    )

    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//div[@id="ownerName"]/div[@class="data"][1]//text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_citrus_taxdeed(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    try:
        sleep(5)
        # try:
        #     wait_for_element(
        #         driver,
        #         xpath='//tr[@class="DataletHeaderBottom"]',
        #     )
        # except Exception as e:
        #     driver.close()
        #     driver.switch_to.window(driver.window_handles[0])
        #     return auction_items

        print("----------------------------------------------------------------")
        response = Selector(text=driver.page_source)
        # owner_name_text = parse(
        #     response,
        #     '//tr[@class="DataletHeaderBottom"]/td[@class="DataletHeaderBottom"][1]/text()',
        # )

        # Find the Parcel ID element using XPath
        parcel_id_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//tr[@class="DataletHeaderTop"]/td[@class="DataletHeaderBottom"]'))
        )

        # Extract text content from the element
        parcel_id_text = parcel_id_element.text.strip()

        # Remove extra spaces
        parcel_id = ' '.join(parcel_id_text.split())

        # Locate the Parcel ID element using XPath
        # parcel_id = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located(
        #         (By.XPATH, "//td[contains(text(), 'Parcel ID')]"))
        # ).text.strip().split(":")[-1].strip()

        print(f"Parcel ID => {parcel_id}")
        parcel_id_split = parcel_id.split(':')[1]
        print(f"Parcel ID After spliting => {parcel_id_split}")

        owner_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "Mailing Address"))
        )

        owner_name = owner_table.find_element(By.XPATH, ".//td[text()='Name']/following-sibling::td").text.strip()
        print(f"Owner Name Text => {owner_name}")
        owner_names = owner_name.split("&")
        owner_names = [x.strip() for x in owner_names if x and str(x).strip()]
        print(f"Owner Names => {owner_names}")

        auction_items["parcel_id"] = parcel_id_split

        for owner_name_idx, owner_name in enumerate(owner_names):
            if owner_name_idx == 0:
                auction_items["full_name"] = owner_name

                print(f'Full Name => {auction_items["full_name"]}')

                first_name = owner_name.split()[0].strip()
                print(f'First Name => {first_name}')
                if len(owner_name.split()) > 1:
                    last_name = " ".join(owner_name.split()[1:]).strip()
                    print(f'Last Name => {last_name}')
                else:
                    last_name = ""

                auction_items["first_name"] = first_name
                auction_items["last_name"] = last_name

            elif owner_name_idx == 1:
                auction_items["alternate_defendant_1"] = owner_name
                print(f'Alternate Defendant 1 => {auction_items["alternate_defendant_1"]}')
            elif owner_name_idx == 2:
                auction_items["alternate_defendant_2"] = owner_name
                print(f'Alternate Defendant 2 => {auction_items["alternate_defendant_2"]}')

        # address_1 = parse(
        #     response,
        #     '//table[@id="Mailing Address"]//td[text()="Mailing Address"]/following-sibling::td/text()',
        # )

        address_1 = owner_table.find_element(By.XPATH, ".//td[text()='Mailing Address']/following-sibling::td").text.strip()

        print(f"Address_1 => {address_1}")
        # address_2 = parse(
        #     response,
        #     '//table[@id="Mailing Address"]//td[text()="Mailing Address"]/parent::tr/following-sibling::tr//text()',
        #     get_method="getall",
        #     space_join=False,
        # )

        address_2 = owner_table.find_element(By.XPATH,
                                            ".//td[text()='Mailing Address']/parent::tr/following-sibling::tr")

        address_2 = address_2.text.strip()
        print(f"Address_2 before joining => {address_2}")

        # address_2 = " ".join([str(x).strip() for x in address_2 if x and str(x).strip()])
        # print(f"Address_2 after joining => {address_2}")

        mailing_address = address_1 + address_2
        auction_items["current_address"] = mailing_address
        print(f'Mailing Address => {auction_items["current_address"]}')

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        print("----------------------------------------------------------------")
        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_volusia_realforeclose(driver, parcel_id_url, auction_items):
    if (
            parcel_id_url
            == "http://publicaccess.vcgov.org/volusia/search/CommonSearch.aspx?mode=REALPROP&UseSearch=no&altpin=TIMESHARE"
    ):
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    response = Selector(text=driver.page_source)

    # click on agree button for volusia county
    if response.xpath('//button[@id="acceptDataDisclaimer"]'):
        click_btn(driver, xpath='//button[@id="acceptDataDisclaimer"]')
        sleep(1)

    try:
        wait_for_element(
            driver,
            xpath='//strong[text()="Owner(s):"]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        '//strong[text()="Owner(s):"]/parent::div/following-sibling::div[@class="col-sm-7"][1]/text()',
        get_method="getall",
        space_join=False,
    )
    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if "-" in owner_name:
            owner_name = owner_name.split("-")[0].strip()

        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//strong[text()="Mailing Address On File:"]/parent::div/following-sibling::div[@class="col-sm-7"][1]/text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_escambia_realforeclose_and_taxdeed(
        driver, parcel_id_url, auction_items
):
    if parcel_id_url == "http://www.escpa.org/cama/Search.aspx":
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)
    try:
        wait_for_element(
            driver,
            xpath='//td[text()="Owners:"]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        '//td[text()="Owners:"]/following-sibling::td/span/text()',
        get_method="getall",
        space_join=False,
    )
    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        owner_name = owner_name.replace("&", "").strip()
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//td[text()="Mail:"]/following-sibling::td/span/text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_lee_realforeclose_and_taxdeed(driver, parcel_id_url, auction_items):
    if (
            parcel_id_url
            == "http://www.leepa.org/Scripts/PropertyQuery/PropertyQuery.aspx?STRAP="
    ):
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        wait_for_element(
            driver,
            xpath='//div[@id="divDisplayParcelOwner"]//div[@class="sectionSubTitle" and contains(., "Owner Of Record")]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    sleep(2)

    response = Selector(text=driver.page_source)
    owner_names_and_addresses_list = parse(
        response,
        '//div[@id="divDisplayParcelOwner"]//div[@class="sectionSubTitle" and contains(., "Owner Of Record")]/following-sibling::div[@class="textPanel"]/div/text()',
        get_method="getall",
        space_join=False,
    )
    owner_names_and_addresses_list = [
        x.strip() for x in owner_names_and_addresses_list if x and str(x).strip()
    ]

    owner_names = []
    addresses = []
    for owner_name_address_idx, owner_name_address in enumerate(
            owner_names_and_addresses_list
    ):
        if owner_name_address_idx == 0:
            owner_names.append(owner_name_address)
            continue

        if "+" in owner_names[-1]:
            owner_names.append(owner_name_address)
        else:
            addresses.append(owner_name_address)

    for owner_name_idx, owner_name in enumerate(owner_names):
        if "+" in owner_name:
            owner_name = owner_name.replace("+", "").strip()
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    auction_items["current_address"] = " ".join(
        [str(x).strip() for x in addresses if x and str(x).strip()]
    )

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_orange_realforeclose(driver, parcel_id_url, auction_items):
    if parcel_id_url == "https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/TIMESHARE":
        return auction_items

    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        wait_for_element(
            driver,
            xpath='//span[text()="Name(s):"]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        '//span[text()="Name(s):"]/following-sibling::span[@class="multiLine"]/text()',
        get_method="getall",
        space_join=False,
    )
    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//span[text()="Mailing Address On File:"]/following-sibling::span/text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_putnam_realtaxdeed(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        card_parent = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "card.card-header.summary-card.p-0.ml-0.mr-0.mb-3"))
        )

        # Wait for the card-body element to be visible
        card_body = WebDriverWait(card_parent, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "card-body"))
        )

        # Find elements using WebDriverWait and XPath
        parcel_id_element = WebDriverWait(card_body, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(text(), 'Parcel')]/following-sibling::div"))
        )
        mailing_address_element = WebDriverWait(card_body, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(text(), 'Mailing Address')]/following-sibling::div"))
        )
        owner_name_element = WebDriverWait(card_body, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(text(), 'Owner')]/following-sibling::div"))
        )

        assessed_value_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//td[contains(text(), 'Just Value of Land')]/following-sibling::td"))
        )

        # Get the text from the elements
        parcel_id = parcel_id_element.text.strip()
        auction_items['parcel_id'] = parcel_id
        mailing_address = mailing_address_element.text.strip().replace("\n", " ")
        auction_items['current_address'] = mailing_address
        owner_name = owner_name_element.text.strip()
        print(f"Initial Owner Name => {owner_name}")
        if "+" in owner_name.lower():
            owner_name_parts = owner_name.split("+")
            owner_name = owner_name_parts[0].strip()
            alt_defendant_1 = owner_name_parts[1].strip()
            auction_items['alternate_defendant_1'] = alt_defendant_1
            print(f"Alternate Defendant for {parcel_id} => {alt_defendant_1}")
        auction_items['full_name'] = owner_name
        assessed_value = assessed_value_element.text.strip()
        auction_items['assessed_value'] = assessed_value

        print(
            f"Parcel ID: {parcel_id} | Mailing Address: {mailing_address} | Owner Name : {owner_name} | Assessed Value : {assessed_value}")

        # try:
        #     wait_for_element(
        #         driver,
        #         xpath='//div[@class="col-4 font-weight-bold" and contains(text(), "Owner")]',
        #     )
        # except Exception as e:
        #     driver.close()
        #     driver.switch_to.window(driver.window_handles[0])
        #     return auction_items
        #
        # response = Selector(text=driver.page_source)
        # owner_names = parse(
        #     response,
        #     '//div[@class="col-4 font-weight-bold" and contains(text(), "Owner:")]/following-sibling::div/text()',
        #     get_method="getall",
        #     space_join=False,
        # )
        # owner_names = [x.strip() for x in owner_names if x and str(x).strip()]
        #
        # for owner_name_idx, owner_name in enumerate(owner_names):
        #     if owner_name_idx == 0:
        #         auction_items["full_name"] = owner_name
        #
        #         first_name = owner_name.split()[0].strip()
        #         if len(owner_name.split()) > 1:
        #             last_name = " ".join(owner_name.split()[1:]).strip()
        #         else:
        #             last_name = ""
        #
        #         auction_items["first_name"] = first_name
        #         auction_items["last_name"] = last_name
        #
        #     elif owner_name_idx == 1:
        #         auction_items["alternate_defendant_1"] = owner_name
        #     elif owner_name_idx == 2:
        #         auction_items["alternate_defendant_2"] = owner_name
        #
        # mailing_address = parse(
        #     response,
        #     '//div[@class="col-4 font-weight-bold" and contains(text(), "Mailing Address:")]/following-sibling::div//text()',
        #     get_method="getall",
        # )
        # auction_items["current_address"] = mailing_address

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return auction_items
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items


def get_owner_info_brevard_realforeclose(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        wait_for_element(
            driver,
            xpath='//button[text()="Owners:"]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        '//div[@data-bind="text: publicOwners"]/text()',
        get_method="getall",
    )
    owner_names = [x.strip() for x in owner_names.split(";") if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split(",")[0].strip()
            if len(owner_name.split(",")) > 1:
                last_name = " ".join(owner_name.split(",")[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        '//div[@data-bind="text: mailingAddress.formatted"]/text()',
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_charlotte_realforeclose(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        wait_for_element(
            driver,
            xpath='//h2[text()="Owner:"]',
        )
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names_addresses = parse(
        response,
        '//h2[text()="Owner:"]/following-sibling::div[1]/text()',
        get_method="getall",
        space_join=False,
    )
    owner_names_addresses = [
        x.strip() for x in owner_names_addresses if x and str(x).strip()
    ]

    mailing_address = " ".join(
        [
            " ".join([str(t).strip() for t in x.split()]).strip()
            for x in owner_names_addresses[-2:]
        ]
    )
    owner_names = []
    for owner_name_address in owner_names_addresses[:-2]:
        owner_name = owner_name_address
        if "&" in owner_name:
            owner_names.extend(
                [x.strip() for x in owner_name.split("&") if x and str(x).strip()]
            )
        elif owner_name.startswith("%"):
            owner_names.append(owner_name.replace("%", "").strip())
        else:
            owner_names.append(owner_name.strip())

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


def get_owner_info_pasco_realforeclose_taxdeed(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        wait_for_element(
            driver,
            xpath='//div[@class="parcelContainerH" and contains(text(), "Mailing Address")]',
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names_addresses = parse(
        response,
        '//span[@id="lblMailingAddress"]//text()',
        get_method="getall",
        space_join=False,
    )
    owner_names_addresses = [
        x.strip() for x in owner_names_addresses if x and str(x).strip()
    ]

    mailing_address = " ".join(
        [
            " ".join([str(t).strip() for t in x.split()]).strip()
            for x in owner_names_addresses[-2:]
        ]
    )
    owner_names = []
    for owner_name_address in owner_names_addresses[:-2]:
        owner_name = owner_name_address
        if "&" in owner_name:
            owner_names.extend(
                [x.strip() for x in owner_name.split("&") if x and str(x).strip()]
            )
        else:
            owner_names.append(owner_name.strip())

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    auction_items["current_address"] = mailing_address

    if not auction_items["assessed_value"]:
        auction_items["assessed_value"] = parse(
            response,
            xpath='//td[text()="Assessed"]/following-sibling::td[last()][@class="datar"]/span[@id="lblSchoolValueAssessed"]/text()',
            get_method="getall",
        )

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items


# TODO: comment this template after testing...
def template(driver, parcel_id_url, auction_items):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(parcel_id_url)

    try:
        wait_for_element(
            driver,
            xpath="",
        )
    except Exception as e:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return auction_items

    response = Selector(text=driver.page_source)
    owner_names = parse(
        response,
        "",
        get_method="getall",
        space_join=False,
    )
    owner_names = [x.strip() for x in owner_names if x and str(x).strip()]

    for owner_name_idx, owner_name in enumerate(owner_names):
        if owner_name_idx == 0:
            auction_items["full_name"] = owner_name

            first_name = owner_name.split()[0].strip()
            if len(owner_name.split()) > 1:
                last_name = " ".join(owner_name.split()[1:]).strip()
            else:
                last_name = ""

            auction_items["first_name"] = first_name
            auction_items["last_name"] = last_name

        elif owner_name_idx == 1:
            auction_items["alternate_defendant_1"] = owner_name
        elif owner_name_idx == 2:
            auction_items["alternate_defendant_2"] = owner_name

    mailing_address = parse(
        response,
        "",
        get_method="getall",
    )
    auction_items["current_address"] = mailing_address

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return auction_items
