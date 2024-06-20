from time import sleep
from parsel import Selector
import pandas as pd
import requests
from urllib.parse import urlparse
from datetime import datetime
import re
import logging
import os
from datetime import datetime
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
    filename='scraper_log_20-june-24(1).log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# define endpoints for CRM API here
# Production endpoint
API_ENDPOINT_PRODUCTION = "http://34.228.119.194:5002/api/AuctionPostAPI"
# testing endpoint
API_ENDPOINT_TESTING = "http://34.228.119.194:5002/api/AuctionPostAPI"

# get today date and time
today_date_time = datetime.now().strftime("%Y-%m-%d_%H-%M")

# booleans for controlling the flow of bot
send_to_api = True
save_to_csv = True
save_to_google_sheets = False
send_alerts_to_telegram = True

current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M")
csv_file_path = f"testing/Without_mapwise_result-{current_datetime}.csv"

# Create directories if they don't exist
os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
print(f"CSV file path: {csv_file_path}")


def main(driver, domain_name, foreclosure_dates):
    """_main logic of the bot_"""

    if save_to_csv:
        # lists to store results for CSV
        results = []
    # Initialize an empty dictionary to store modified data
    modified_urls_to_scrape = {}

    rows_to_input_in_csv = 0
    total_urls = 0
    
    print("")
    print("")
    print("")
    pprint(foreclosure_dates)

    # loop through each foreclosure date and scrape the data
    for f_d_idx, foreclosure_date in enumerate(foreclosure_dates):
        print("----------------------------------------------------------------")
        print(f"{f_d_idx + 1}/{len(foreclosure_dates)} | Processing for foreclosure Date => {foreclosure_date}")
        print("----------------------------------------------------------------")
        # generate auction link from domain name and foreclosure date
        auction_link = generate_auction_link(domain_name, foreclosure_date)
        print(f"Auction Link | {auction_link}")
        if save_to_google_sheets:
            # list to store results for google sheets
            results_for_google_sheets = []

        try:
            rd = 1
            # get the auction link
            driver.get(auction_link)
            page_no = 1

            # flag to check if all pages are done
            all_pages_done = False
            # flag to check if there are no auction present
            no_auction_rows = False
            
            # infinite loop to handle pagination
            while True:
                # wait for the loading of page
                wait_for_loading(driver)
                sleep(1.5)
                # save the response
                response = Selector(text=driver.page_source)
                # rows of auctions, where each row in 1 auction
                auction_rows = response.xpath(
                    '//div[@class="Head_W"]//div[contains(@class,"AUCTION_ITEM PREVIEW")]'
                )
                print("----------------------------------------------------------")
                pprint(f"Auction Rows for {foreclosure_date} => {len(auction_rows)}")
                print("----------------------------------------------------------")

                row_idx = 1
                # Iterate through each auction row and extract data
                for row in auction_rows:
                    print(f"Processing {row_idx}/{len(auction_rows)}")
                    parsed_url = urlparse(url)
                    print(parsed_url)

                    # Get the subdomain from the URL
                    subdomain = parsed_url.netloc.split('.')[0]

                    print("County Name:", subdomain)

                    print(f"Processing row {rd}")
                    if subdomain.lower() == 'myorangeclerk':
                        try:
                            # get the auction items and parcel id url
                            auction_items, parcel_id_url = get_orange_items(
                                row, foreclosure_date, auction_link, subdomain
                            )
                        except:
                            print("Continuing From OrangeCLERK")
                            continue
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
                    print(f"AUCTION ITEM # For {subdomain} | => ")
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

                    print("-------------------------------------------------")
                    # # send the data to csv if flag is enabled
                    # if save_to_csv:
                    #     if auction_items not in results:
                    #         results.append(auction_items)
                    #     df = pd.DataFrame(results)
                    #     df.to_csv(
                    #         "testing\escambia.csv",
                    #         index=False,
                    #         encoding="utf-8-sig",
                    #     )
                    #     logging.info("---------------------")
                    #     logging.info("| Data added in csv |")
                    #     logging.info("---------------------")

                    #     print("---------------------")
                    #     print("| Data added in csv |")
                    #     print("---------------------")
                    

                    if save_to_csv:
                        # Convert the auction_items to a DataFrame
                        df = pd.DataFrame([auction_items])

                        # Check if the file already exists
                        file_exists = os.path.isfile(csv_file_path)
                        
                        if file_exists:
                            # Append data to the existing file without writing the header
                            df.to_csv(csv_file_path, mode='a', header=False, index=False, encoding="utf-8-sig")
                        else:
                            # Write data to a new file with the header
                            df.to_csv(csv_file_path, mode='w', header=True, index=False, encoding="utf-8-sig")
                        
                        logging.info("---------------------")
                        logging.info("| Data added in csv |")
                        logging.info("---------------------")

                        print("---------------------")
                        print("| Data added in csv |")
                        print("---------------------")


                    # save the data to google sheets list if flag is enabled
                    if save_to_google_sheets:
                        if auction_items not in results_for_google_sheets:
                            results_for_google_sheets.append(auction_items)

                    rd += 1
                    total_urls += 1
                    row_idx += 1

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
                    print("All Pages Done!!")
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

        # if any error occurs continue to the next retry, if no retry left continue to the next auction link
        except Exception as e:
            print(f"Error Occurred in the main function: {e}")
            logging.exception(f"Error Occurred in the main function: {e}")
            continue

        # if flag is enabled send the data to google sheets
        if save_to_google_sheets:
            send_to_google_sheets(results_for_google_sheets)

    print(f"total_urls = {total_urls},")
    
    return rows_to_input_in_csv


    # close the browser
    # driver.close()

def get_to_mapwise_func(driver):
    search(driver)

    processed_data = pd.read_csv(csv_file_path)

    modified_data = []

    for index, row in processed_data.iterrows():
        row_str = {key: str(value) for key, value in row.items()}

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
            owner_address = row_str['current_address']

            print("---------------------------------------------")
            print(auction_link__)
            print("---------------------------------------------")

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

        for key, value in row_str.items():
            if value == "nan":
                row_str[key] = "0"

        print("Printing Row Before Sending to CRM")
        pprint(row_str)
        
        try:
            if ',' in row_str['full_name']:
                parts__ = row_str['full_name'].split(',')
                if len(parts__) == 2:
                    row_str['first_name'] = parts__[0].strip()
                    print(f"first_name After Splitting: {row_str['first_name']}")
                    row_str['last_name'] = parts__[1].strip()
                    print(f"last_name After Splitting: {row_str['last_name']}")
                if len(parts__) >= 3:
                    row_str['full_name'] = parts__[0].strip()
                    print(f"Full Name After Splitting: {row_str['full_name']}")
                    row_str['alternate_defendant_1'] = parts__[1].strip()
                    print(f"Alternative Defendant 1 After Splitting: {row_str['alternate_defendant_1']}")
                    row_str['alternate_defendant_2'] = parts__[2].strip()
                    print(f"Alternative Defendant 2 After Splitting: {row_str['alternate_defendant_2']}")
            else:
                print(f"Hmm, Full Name => {row_str['full_name']}")
        except:
            print(f"Hmm, Full Name => {row_str['full_name']}")


        if send_to_api:
            url_tcpa_law = API_ENDPOINT_PRODUCTION
            print("Sending to API NOW!!!")
            tcpa_law_auction_status = requests.post(
                url=url_tcpa_law, json=row_str
            )
            print(tcpa_law_auction_status.text)

    print(f"---------------------MODIFIED DATA-----------------------")
    pprint(modified_data)
    # Convert the modified data list to a DataFrame
    modified_df = pd.DataFrame(modified_data)

    # Write the modified DataFrame back to the CSV file
    modified_df.to_csv(f"testing/mapwise_result-{current_datetime}.csv", index=False)


# run the main function
if __name__ == "__main__":
    if send_alerts_to_telegram:
        current_time_in_est = get_current_time_in_est_12hr_format()
        message_to_send = "NEW Bot 1 | STARTED running at {}".format(
            current_time_in_est
        )
        send_message_to_telegram(message_to_send)
        print(message_to_send)
    # setup the bot
    driver = bot_setup()
    
    # get the list of urls to scrape i.e county urls
    urls_to_scrape = get_urls_from_file()
    
    # loop through each url and scrape the data
    for url_idx, (url, data) in enumerate(urls_to_scrape.items(), start=1):
        try:
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
                    pprint(foreclosure_dates)
                    break
                except:
                    continue
            else:
                print("Error in getting foreclosure dates for -> {}".format(domain_name))
                logging.exception("Error in getting foreclosure dates for -> {}".format(domain_name))

            # if no foreclosure dates are present we continue to the next url
            if not foreclosure_dates:
                continue
            
            rows_to_input_in_csv = main(driver, domain_name, foreclosure_dates)
            
        except Exception as e:
            print(f"Error in => {url} | Error: {e}")
            logging.exception(f"Error in => {url} | Error: {e}")
            continue
        
    driver.quit()
    print(f"Total rows processed all over the run!!! => {rows_to_input_in_csv}")
        
    driver = bot_setup()
    get_to_mapwise_func(driver)
    driver.quit()
    if send_alerts_to_telegram:
        current_time_in_est = get_current_time_in_est_12hr_format()
        message_to_send = "NEW Bot 1 | FINISHED running at {}".format(
            current_time_in_est
        )
        send_message_to_telegram(message_to_send)
        print(message_to_send)


    # infinite loop to keep the bot running until all the data is scraped
    # while True:
        # try:
            # if send_alerts_to_telegram:
            #     current_time_in_est = get_current_time_in_est_12hr_format()
            #     message_to_send = "Bot 1 has STARTED running at {}".format(
            #         current_time_in_est
            #     )
            #     send_message_to_telegram(message_to_send)
            #     print(message_to_send)

            # run the main function
            # main()

            # if send_alerts_to_telegram:
            #     current_time_in_est = get_current_time_in_est_12hr_format()
            #     message_to_send = "Bot 1 has FINISHED running at {}".format(
            #         current_time_in_est
            #     )
            #     send_message_to_telegram(message_to_send)
            #     print(message_to_send)
            # break
        # except:  # if any error occurs continue to the next retry
            # print("ERRORRRRRRRRRRRRRRRRRRR")
                # if send_alerts_to_telegram:
                #     current_time_in_est = get_current_time_in_est_12hr_format()
                #     message_to_send = "Bot 1 has STOPPED running at {}\nTrying Again".format(
                #         current_time_in_est
                #     )
                #     send_message_to_telegram(message_to_send)
                # test
                # import traceback
                # print(traceback.format_exc())
                # input("Press Enter to continue...")
                # continue

    # main()
    # print("Excel File mapwise status updated!!!")
    # logging.info("Excel File mapwise status updated!!!")
