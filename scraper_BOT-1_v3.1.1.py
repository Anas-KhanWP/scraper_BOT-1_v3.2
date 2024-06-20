import json
from time import sleep
from parsel import Selector
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime
import re
import logging

from selenium.webdriver.common.by import By

from helper_functions_v2 import (
    parse,
    get_urls_from_file,
    generate_auction_link,
    bot_setup,
    click_btn,
    get_foreclosure_dates_from_calendar,
    wait_for_loading,
    get_items,
    send_to_google_sheets,
    get_owner_info,
    send_message_to_telegram,
    get_current_time_in_est_12hr_format,
    check_mapwise, get_orange_items,
)

from pprint import pprint

from mapwise import (
    search,
    map_main
)

# Configure logging
logging.basicConfig(
    filename='scraper_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# define endpoints for CRM API here
# Production endpoint
API_ENDPOINT_PRODUCTION = "http://34.228.119.194/api/AuctionPostAPI"

# testing endpoint
API_ENDPOINT_TESTING = "http://34.228.119.194:5002/api/AuctionPostAPI"

# get today date and time
today_date_time = datetime.now().strftime("%Y-%m-%d_%H-%M")

# booleans for controlling the flow of bot
send_to_api = True
save_to_csv = True
save_to_google_sheets = False
send_alerts_to_telegram = True


# Function to replace 'nan' with '0'
def replace_nan_with_zero(data):
    for key, value in data.items():
        if value == "nan":
            data[key] = "0"

    return data


def main():
    """_main logic of the bot_"""

    if save_to_csv:
        # lists to store results for CSV
        results = []

    # get the list of urls to scrape i.e county urls
    urls_to_scrape = get_urls_from_file()
    print()

    # # testing input
    # urls_to_scrape = urls_to_scrape[:2]
    # urls_to_scrape = [
    #     # "https://brevard.realforeclose.com/index.cfm?resetcfcobjs=1",
    #     # "https://miamidade.realforeclose.com/",
    #     # "https://duval.realforeclose.com/",
    #     # "https://lee.realforeclose.com/",
    #     # "https://clay.realforeclose.com/",
    # ]
    # urls_to_scrape = [
    #     x.split("?")[0] + "?zaction=USER&zmethod=CALENDAR" for x in urls_to_scrape
    # ]

    # setup the bot
    driver = bot_setup()

    # Initialize an empty dictionary to store modified data
    modified_urls_to_scrape = {}

    rows_to_input_in_csv = 0
    # loop through each url and scrape the data
    for url_idx, (url, data) in enumerate(urls_to_scrape.items(), start=1):
        total_urls = 0
        print("Started Scraping URL -> {}/{}".format(url_idx, len(urls_to_scrape)))
        logging.info("Started Scraping URL -> {}/{}".format(url_idx, len(urls_to_scrape)))
        pprint(data)
        # get the domain name from the url
        domain_name = urlparse(url).netloc
        # open the url in the browser
        driver.get(data['modified_url'])
        sleep(2)

        print("-------------------------------------------------")
        print(
            "Getting Foreclosure Dates For -> {}/{}".format(
                url_idx, len(urls_to_scrape)
            )
        )
        logging.info(
            "Getting Foreclosure Dates For -> {}/{}".format(
                url_idx, len(urls_to_scrape)
            )
        )
        print("-------------------------------------------------")

        # get the foreclosure dates from the calendar
        foreclosure_dates = []
        for _ in range(3):
            try:
                foreclosure_dates = get_foreclosure_dates_from_calendar(driver)
                break
            except:
                continue
        else:
            print("Error in getting foreclosure dates for -> {}".format(domain_name))
            logging.exception("Error in getting foreclosure dates for -> {}".format(domain_name))

        # if no foreclosure dates are present we continue to the next url
        if not foreclosure_dates:
            continue

        # # test
        # foreclosure_dates = foreclosure_dates[:1]

        # test = 0
        status = False

        # loop through each foreclosure date and scrape the data
        for f_d_idx, foreclosure_date in enumerate(foreclosure_dates):
            # if f_d_idx <= 1:
            print("----------------------------------------------------------------")
            print(f"{f_d_idx + 1}/{len(foreclosure_dates)} | Processing for foreclosure Date => {foreclosure_date}")
            print("----------------------------------------------------------------")
            # generate auction link from domain name and foreclosure date
            auction_link = generate_auction_link(domain_name, foreclosure_date)
            if save_to_google_sheets:
                # list to store results for google sheets
                results_for_google_sheets = []

            # try_auction_range = 1
            # we try for 3 times for each auction link
            # for _ in range(3):
            try:
                print(f"try each auction link")
                # get the auction link
                driver.get(auction_link)
                page_no = 1

                # flag to check if all pages are done
                all_pages_done = False
                # flag to check if there are no auction present
                no_auction_rows = False

                rows_list = []
                # infinite loop to handle pagination
                while True:
                    # if len(rows_list) >= 10:
                    #     print(f"rows List => {len(rows_list)}")
                    #     break

                    # wait for the loading of page
                    wait_for_loading(driver)
                    sleep(4)
                    # save the response
                    response = Selector(text=driver.page_source)
                    # rows of auctions, where each row in 1 auction
                    auction_rows = response.xpath(
                        '//div[@class="Head_W"]//div[contains(@class,"AUCTION_ITEM PREVIEW")]'
                    )
                    print("----------------------------------------------------------")
                    pprint(f"Auction Rows for {foreclosure_date} => {auction_rows}")
                    print("----------------------------------------------------------")
                    # if there are no auction rows set the flag to false, and break
                    if not auction_rows:
                        print("No auction rows")
                        no_auction_rows = True
                        break

                    # Iterate through each auction row and extract data
                    for auc_row in auction_rows:
                        rows_list.append(auc_row)

                    rd = 1
                    rows_to_input_in_csv += len(rows_list)

                    # get the current page and total pages
                    current_page = parse(
                        response,
                        '(//div[@class="Head_W"]//input[@curpg])[1]/@curpg',
                    )
                    total_pages = parse(
                        response,
                        '(//div[@class="Head_W"]//span[@id="maxWA"])[1]/text()',
                    )
                    # if current page is not equal to total pages click the next page button
                    if current_page != total_pages:
                        sleep(1)
                        click_btn(
                            driver,
                            xpath='(//div[@class="Head_W"]//span[@class="PageRight"])[1]',
                        )
                        sleep(2)
                    else:  # if current page is equal to total pages set the flag to true and break
                        print(f"{current_page}/{total_pages} Done")
                        all_pages_done = True
                        break

                    print(f"")

                    print("-------------------------------------------------")
                    print(
                        "URL Index -> {}/{}".format(
                            url_idx, len(urls_to_scrape)
                        )
                    )
                    print(
                        "Foreclosure Date Index -> {}/{}".format(
                            f_d_idx + 1, len(foreclosure_dates)
                        )
                    )
                    print("Page No -> {}".format(page_no))
                    print("-------------------------------------------------")
                    page_no += 1

                    # loop through each auction

                print(f"Total Rows in current list => {len(rows_list)}")
                total_urls += len(rows_list)
                print(f"Total URLS Processed => {total_urls}")

                # if total_urls >= 10:
                for row in rows_list:
                    parsed_url = urlparse(url)
                    print(parsed_url)

                    # Get the subdomain from the URL
                    subdomain = parsed_url.netloc.split('.')[0]

                    print("County Name:", subdomain)

                    print(f"Processing row {rd}")
                    if subdomain.lower() == 'myorangeclerk':
                        # get the auction items and parcel id url
                        auction_items, parcel_id_url = get_orange_items(
                            row, foreclosure_date, auction_link, subdomain
                        )

                    else:
                        # get the auction items and parcel id url
                        auction_items, parcel_id_url = get_items(
                            row, foreclosure_date, auction_link, subdomain
                        )

                    auction_items['county'] = subdomain

                    print(f"Domain => {auction_items['county']} Parcel ID URL => {parcel_id_url}")

                    if str(auction_items['parcel_id']).lower() == 'timeshare' or auction_items['parcel_id'] == "":
                        print(f"Parcel_id is => {auction_items['parcel_id']}")
                        print(f"Parcel_id url => {parcel_id_url}")

                    # if parcel id url is present get the owner info, (name, address)
                    if (
                            parcel_id_url
                    ):
                        print(f"Parcel_id => {auction_items['parcel_id']}")
                        auction_items = get_owner_info(
                            driver,
                            domain_name,
                            parcel_id_url,
                            auction_items,
                        )

                    if subdomain.lower() == 'myorangeclerk':
                        subdomain = 'Orange'
                    if subdomain == 'miamidade':
                        subdomain = 'Miami-Dade'

                    auction_items['county'] = subdomain

                    # pretty print the auction items
                    pprint(auction_items)

                    print(f"total rows processed so far => {rd}")

                    print("-------------------------------------------------")
                    print(
                        "URL Index -> {}/{}".format(
                            url_idx, len(urls_to_scrape)
                        )
                    )
                    print(
                        "Foreclosure Date Index -> {}/{}".format(
                            f_d_idx + 1, len(foreclosure_dates)
                        )
                    )
                    print("Page No -> {}".format(page_no))

                    # send data to api if flag is enabled
                    # if send_to_api:
                    #     url_tcpa_law = API_ENDPOINT_PRODUCTION
                    #     tcpa_law_auction_status = requests.post(
                    #         url=url_tcpa_law, json=auction_items
                    #     )
                    #     print(tcpa_law_auction_status.text)
                    print("-------------------------------------------------")
                    # send the data to csv if flag is enabled
                    if save_to_csv:
                        if auction_items not in results:
                            results.append(auction_items)
                        df = pd.DataFrame(results)
                        df.to_csv(
                            "testing/mdade.csv",
                            index=False,
                            encoding="utf-8-sig",
                        )

                    # save the data to google sheets list if flag is enabled
                    if save_to_google_sheets:
                        if auction_items not in results_for_google_sheets:
                            results_for_google_sheets.append(auction_items)

                    rd += 1

                    # if total_urls >= 10:
                    #     break

                    # if all pages are done break the loop
                    if all_pages_done:
                        break

                    # if no auction rows are present break the loop
                    if no_auction_rows:
                        print("NO AUCTION ROWS AT THE END!!!")
                        break
                    # test += 1

                    # if test == 5:
                    #     status = True
                    #     print("breaking from loops")
                    #     break

            # if any error occurs continue to the next retry, if no retry left continue to the next auction link
            except Exception as e:
                # import traceback
                # print(traceback.format_exc()) # test
                # sleep(6000)
                print(f"Error Occurred in the main function: {e}")
                logging.exception(f"Error Occurred in the main function: {e}")
                continue

            # if status:
            #     print("Breaking from parents")
            #     break

            # if flag is enabled send the data to google sheets
            if save_to_google_sheets:
                send_to_google_sheets(results_for_google_sheets)

            print(f"total_urls = {total_urls},")

            # if total_urls >= 10:
            #     print(f"total_urls = {total_urls}, moving to next url")
            #     break

        # Create a modified copy of data with 'mapwise' set to False
        # modified_data = data.copy()
        # modified_data['mapwise'] = False
        #
        # # Append modified data to the new dictionary
        # modified_urls_to_scrape[url] = modified_data

    # close the browser
    driver.close()
    driver.quit()
    print(f"Total rows processed all over the run!!! => {rows_to_input_in_csv}")
    # Convert modified dictionary to DataFrame
    # df_modified = pd.DataFrame(modified_urls_to_scrape).T.reset_index()
    # print(df_modified.shape)  # This will print the shape of the DataFrame
    #
    # # Check the existing column names
    # print(df_modified.columns)
    #
    # # Assign column names for all three columns
    # df_modified.columns = ['URL', 'mapwise', 'modified_url']
    #
    # # Save the DataFrame to an Excel file
    # df_modified.to_excel('input_v3.1.1.xlsx', index=False)

    # print("Excel File mapwise status updated!!!")

    driver = bot_setup()
    search(driver)
    # scraper = MapWiseScraper()
    # scraper.run(driver)

    processed_data = pd.read_csv(r"testing\mdade.csv")

    modified_data = []

    for index, row in processed_data.iterrows():
        row_str = {key: str(value) for key, value in row.items()}
        # print("---------------------------------------------")
        # pprint(row_str)
        # print("---------------------------------------------")

        try:
            if "e" in row_str['parcel_id'] or "E" in row_str['parcel_id']:
                print(f"Parcel_id is => {row_str['parcel_id']}")
                # Convert scientific notation string to float and then to integer
                row_str['parcel_id'] = int(float(row_str['parcel_id']))
                print(f"Parcel_id CONVERTED => {row_str['parcel_id']}")
        except Exception as e:
            print(f"Error Occurred while converting parcel id: {e}")

        try:
            judgement_amount = row_str['final_judgment_amount']
            assessment_value = row_str['assessed_value']
            parcel_id = row_str['parcel_id']
            property_street = row_str['property_street']
            auction_link__ = row_str['auction_link']
            owner_name = row_str['full_name']
            owner_address = row_str['Current Address']

            print("---------------------------------------------")
            print(auction_link__)
            print("---------------------------------------------")

            # row['assessment_amount']
            # row['final_judgment_amount']

            # if (
            #     owner_name.lower() != "nan" and owner_address.lower() != "nan"
            # ):
            #     print("Detail Already filled")

            if (
                    assessment_value.lower() != "nan"
                    and judgement_amount.lower() != "nan" and
                    str(parcel_id).lower() not in ["property appraiser", "timeshare", "", "multiple parcels",
                                                   "multiple parcel", "nan"]
            ):
                print(f"Assessment value {assessment_value} and Judgement amount {judgement_amount}")

                # Remove special characters from judgement_amount and assessment_value
                final_judgment_amount = re.sub(r'[^\d.]', '', str(judgement_amount))
                final_assessment_amount = re.sub(r'[^\d.]', '', str(assessment_value))

                # Convert to float if the value is not empty after removing special characters
                if final_judgment_amount:
                    final_judgment_amount = float(final_judgment_amount)
                    row_str['final_judgment_amount'] = str(final_judgment_amount)
                else:
                    print("Final Judgment Amount is empty after removing special characters. Skipping conversion.")
                    final_judgment_amount = None

                if final_assessment_amount:
                    final_assessment_amount = float(final_assessment_amount)
                    row_str['assessed_value'] = str(final_assessment_amount)
                else:
                    print("Final Assessment Amount is empty after removing special characters. Skipping conversion.")
                    final_assessment_amount = None

                # Call check_mapwise function if both values are valid
                if final_assessment_amount is not None and final_judgment_amount is not None:
                    print("Sending converted float assessment and judgement values to mapwise")
                    modified_row = check_mapwise(row_str, driver)
                    if modified_row is not None:
                        print("Modified data not None")
                        print("--------------------------------------------------------")
                        pprint(modified_row)
                        print("--------------------------------------------------------")
                        modified_data.append(modified_row)
                    elif modified_row is None:
                        print("Modified data IS None!!!")
                        modified_data.append(row_str)

            elif (
                    assessment_value != "nan"
                    and judgement_amount != "nan"
                    and property_street not in ["nan", '', 'null, null null']
            ):
                print(
                    f"elif logic => Assessment value: {assessment_value} and Judgement amount: {judgement_amount} and parcel_id: {parcel_id}"
                )
                # Remove special characters from judgement_amount and assessment_value
                final_judgment_amount = re.sub(r'[^\d.]', '', str(judgement_amount))
                if final_judgment_amount:
                    final_judgment_amount__ = float(final_judgment_amount)
                    row_str['final_judgment_amount'] = str(final_judgment_amount__)
                    modified_row = check_mapwise(row_str, driver)
                    if modified_row is not None:
                        print("Modified data not None")
                        print("--------------------------------------------------------")
                        pprint(modified_row)
                        print("--------------------------------------------------------")
                        modified_data.append(modified_row)
                    elif modified_row is None:
                        print("Modified data IS None!!!")
                        modified_data.append(row_str)
            elif (
                    pd.isnull(assessment_value) or assessment_value in ['nan', '']
            ):
                print(f'Assessment Value is FAULTY => {assessment_value}')
                modified_row = check_mapwise(row_str, driver, fault_status=True)
                if modified_row is not None:
                    print("Recovered From Faulty... Modified data not None")
                    print("--------------------------------------------------------")
                    pprint(modified_row)
                    print("--------------------------------------------------------")
                    modified_data.append(modified_row)
                elif modified_row is None:
                    print("Modified data IS None!!!")
                    modified_data.append(row_str)
            else:
                print("Value is null")
                print(f"NULL But Here You Go!!! Assessment Val =>")
                pprint({row_str})
                modified_data.append(row_str)
        except Exception as e:
            print(f"(Error) => {e}")
            modified_data.append(row_str)
            continue

        print(f"Data To Send To CRM is:")
        pprint(row_str)

        # data_dict = json.loads(row_str)
        # print("Data_Dict:")
        # pprint(data_dict)
        # Apply the function
        # new_row = replace_nan_with_zero(row_str)

        for key, value in row_str.items():
            if value == "nan":
                row_str[key] = "0"

        print("Updated row!!!")
        pprint(row_str)

        test_input = input("Do You want to continue with sending this to API? (y/n/exit): ")
        if test_input.lower() == 'yes':
            if send_to_api:
                url_tcpa_law = API_ENDPOINT_PRODUCTION
                print("Sending to API NOW!!!")
                tcpa_law_auction_status = requests.post(
                    url=url_tcpa_law, json=row_str
                )
                print(tcpa_law_auction_status.text)
        if test_input.lower() == 'n':
            continue

        if test_input.lower() == 'exit':
            exit()

    print(f"---------------------MODIFIED DATA-----------------------")
    pprint(modified_data)
    # Convert the modified data list to a DataFrame
    modified_df = pd.DataFrame(modified_data)

    # Write the modified DataFrame back to the CSV file
    modified_df.to_csv("testing_v2\omdade.csv", index=False)


# run the main function
if __name__ == "__main__":
    # infinite loop to keep the bot running until all the data is scraped
    while True:
        try:
            if send_alerts_to_telegram:
                current_time_in_est = get_current_time_in_est_12hr_format()
                message_to_send = "Bot 1 has STARTED running at {}".format(
                    current_time_in_est
                )
                send_message_to_telegram(message_to_send)
                print(message_to_send)

            # run the main function
            main()

            if send_alerts_to_telegram:
                current_time_in_est = get_current_time_in_est_12hr_format()
                message_to_send = "Bot 1 has FINISHED running at {}".format(
                    current_time_in_est
                )
                send_message_to_telegram(message_to_send)
                print(message_to_send)
            break
        except:  # if any error occurs continue to the next retry
            if send_alerts_to_telegram:
                current_time_in_est = get_current_time_in_est_12hr_format()
                message_to_send = "Bot 1 has STOPPED running at {}\nTrying Again".format(
                    current_time_in_est
                )
                send_message_to_telegram(message_to_send)
            # test
            # import traceback
            # print(traceback.format_exc())
            # input("Press Enter to continue...")
            continue

    # main()
    # print("Excel File mapwise status updated!!!")
    # logging.info("Excel File mapwise status updated!!!")
