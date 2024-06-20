import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from pprint import pprint
# from helper_functions_v2 import bot_setup
# import copy
import re


def search(driver):
    driver.execute_script("window.open('', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get("https://www.mapwise.com/members/login.php")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "email"))).send_keys(
        "cases@surplusagentsforamericans.com")
    password = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "pass")))
    password.send_keys("Surplus12$")
    password.send_keys(Keys.ENTER)
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//a[normalize-space(text())='Start MapWise Web App']"))).click()
    sleep(0.5)
    driver.close()
    new_tab = driver.window_handles[-1]
    driver.switch_to.window(new_tab)


def go_to_parcel(driver):
    parcel = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Parcels']")))
    sleep(5)
    parcel.click()
    sleep(0.5)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "ext-gen95"))).click()


def map_main(driver, row, val=False, get_address=True, get_assessment=False):
    try:
        go_to_parcel(driver)
    except:
        print("Unclickable element")

    try:
        sleep(0.5)
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "ext-gen95"))).click()
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "formSearchAddress1"))).clear()
    except Exception as e:
        print(f"Error => {e}")

    county_selector = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "formSearchCounty")))
    try:
        time.sleep(2)
        county_selector.click()
    except Exception as e:
        print(f"Error while clicking county => {e}")

    try:
        if row['county'].lower() == 'saintjohns':
            row['county'] = 'St Johns'
        if row['county'].lower() == 'santarosa':
            row['county'] = 'Santa Rosa'
        if row['county'].lower() == 'stlucie':
            row['county'] = 'St Lucie'
        if row['county'].lower() == 'miamidade':
            row['county'] = 'Miami-Dade'
        if row['county'].lower() == 'indian-river':
            row['county'] = 'Indian River'
        if row['county'].lower() == 'myorangeclerk':
            row['county'] = 'Orange'
        print(f"County: {row['county']}")

        xpath_expression = f"//div[contains(@class,'x-combo-list-item') and text()='{row['county'].capitalize()}']"
        element = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_expression)))
        element.click()
    except Exception as e:
        print(f"County not listed")
        xpath_expression = f"//div[contains(@class,'x-combo-list-item') and text()='All Counties']"
        element = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_expression)))
        element.click()

    parcel_input = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "formSearchPin1")))
    search__ = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "formSearchAddress1")))

    try:
        if (
                not pd.isnull(row['parcel_id']) and isinstance(row['parcel_id'], str)
                and str(row['parcel_id']).lower() not in ["property appraiser", "timeshare", "",
                                                          "multiple parcels",
                                                          "multiple parcel", "nan"]
        ):
            parcel_input.click()
            search__.clear()
            parcel_input.clear()
            parcel_input.send_keys(row['parcel_id'])
            parcel_input.send_keys(Keys.ENTER)

            print(f"(In Except Condition) => Parcel ID => {row['parcel_id']}")
            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//a[normalize-space(text())='Property Details']"))
            ).click()
            # try:
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            just_value = row['assessed_value']

            if val:
                just_value_element = soup.find('td', text='Just Value:').find_next('td')
                just_value = just_value_element.get_text(strip=True)

                row['assessed_value'] = just_value
                print(f"Just Value: {row['assessed_value']}")

            if get_assessment:
                assessed_value_element = soup.find('td', text='Assessed Value:').find_next('td')
                assessed_value = assessed_value_element.get_text(strip=True)

                row['assessed_value'] = assessed_value
                print(f"Assessed Value from get_assessment: {row['assessed_value']}")
            if get_address:
                owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                if "&amp;" in owner_name_element:
                    owner_name_element = owner_name_element.replace('&amp;', '&')
                print(f"Owner Name ELEMENT => {owner_name_element}")
                # owner_name = owner_name_element.get_text(strip=True)
                if owner_name_element:
                    row['full_name'] = owner_name_element
                    print(f"Owner Name: {row['full_name']}")
                else:
                    print(f"Owner Name Not Found!!!")

                mailing_address_element = soup.find('td', text='Mailing Address:')

                mailing_address = mailing_address_element.find_next('td').get_text(strip=True)
                if mailing_address:
                    row['current_address'] = mailing_address
                    print(f"Mailing address => {row['current_address']}")
                else:
                    print("Mailing Address Not Found!!!")

                defendants = []
                try:
                    owner_name_parts = re.split(r'&|AND|\n', row['full_name'], flags=re.IGNORECASE)
                    
                    pprint(owner_name_parts)

                    if len(owner_name_parts) >= 2:
                        for part in owner_name_parts:
                            # Split each part by '&'
                            split_ = part.split(",")
                            print(f"Part => {split_}")
                            defendants.extend(split_)
                        print(f"Defendants length => {len(defendants)}")
                        if len(defendants) == 2:
                            row['full_name'] = defendants[0]
                            row['alternate_defendant_1'] = defendants[1]

                        if len(defendants) >= 3:
                            row['full_name'] = defendants[0]
                            row['alternate_defendant_1'] = defendants[1]
                            row['alternate_defendant_2'] = defendants[2]
                            print(
                                f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                            )
                except Exception as e:
                    print(f"Error occurred while finding owner name parts: {e}")
                    owner_name_parts = row['full_name'].split(",")
                    if owner_name_parts >= 2:
                        row['last_name'], row['first_name'] = owner_name_parts

            pprint(row) if row else print("Row did not modified")
            return row if row else row
        elif (
                pd.notnull(row['property_street']) and isinstance(row['property_street'], str)
                and str(row['property_street']).lower() not in ["", "nan"]
        ):
            try:
                go_to_parcel(driver)
                search__.clear()
                parcel_input.clear()
                print(f"Row street address => {row['property_street']}")
                search__.send_keys(row['property_street'])
                search__.send_keys(Keys.ENTER)

                rows = WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "x-grid3-row")))

                for row__ in rows:
                    try:
                        if (
                                not pd.isnull(row['parcel_id']) and isinstance(row['parcel_id'], str)
                                and str(row['parcel_id']).lower() not in ["property appraiser", "timeshare", "",
                                                                          "multiple parcels",
                                                                          "multiple parcel", "nan"]
                        ):
                            print("In if Conditions")
                            numeric_string = ''.join(filter(str.isdigit, str(row['parcel_id'])))
                            print(f"Numeric string => {numeric_string}")
                            pin = WebDriverWait(row__, 120).until(EC.presence_of_element_located((By.XPATH,
                                                                                                  "//td[@class='x-grid3-col x-grid3-cell x-grid3-td-3 x-selectable ']/div[@class='x-grid3-cell-inner x-grid3-col-3']"))).text

                            pin_string = ''.join(filter(str.isdigit, pin))
                            print(f"Pin string => {pin_string}")

                            if pin_string == numeric_string:
                                print(f"Found parcel with id: {row['parcel_id']}")
                                WebDriverWait(row__, 120).until(EC.presence_of_element_located(
                                    (By.XPATH, "//a[normalize-space(text())='Property Details']"))).click()

                                try:
                                    time.sleep(5)
                                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    just_value = row['assessed_value']

                                    if val:
                                        just_value_element = soup.find('td', text='Just Value:').find_next('td')
                                        just_value = just_value_element.get_text(strip=True)

                                        row['assessed_value'] = just_value

                                    if get_assessment:
                                        assessed_value_element = soup.find('td', text='Assessed Value:').find_next('td')
                                        assessed_value = assessed_value_element.get_text(strip=True)

                                        row['assessed_value'] = assessed_value
                                        print(f"Assessed Value from get_assessment: {row['assessed_value']}")

                                    if get_address:
                                        owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                                        if "&amp;" in owner_name_element:
                                            owner_name_element = owner_name_element.replace('&amp;', '&')
                                        print(f"Owner Name ELEMENT => {owner_name_element}")
                                        # owner_name = owner_name_element.get_text(strip=True)
                                        if owner_name_element:
                                            row['full_name'] = owner_name_element
                                            print(f"Owner Name: {owner_name_element}")
                                        else:
                                            print("Owner Name Not Found!!!")

                                        mailing_address_element = soup.find('td', text='Mailing Address:')
                                        mailing_address = mailing_address_element.find_next('td').get_text(strip=True)
                                        if mailing_address:
                                            print(f"Mailing address => {mailing_address}")
                                            row['current_address'] = mailing_address
                                        else:
                                            print("Mailing Address Not Found!!!")

                                        defendants = []
                                        try:
                                            owner_name_parts = re.split(r'&|AND|\n', row['full_name'],
                                                                        flags=re.IGNORECASE)

                                            if len(owner_name_parts) >= 2:
                                                for part in owner_name_parts:
                                                    split_ = part.split(",")
                                                    print(f"Part => {split_}")
                                                    defendants.extend(split_)
                                                print(f"Defendants length => {len(defendants)}")
                                                if len(defendants) >= 3:
                                                    row['full_name'] = defendants[0]
                                                    row['alternate_defendant_1'] = defendants[1]
                                                    row['alternate_defendant_2'] = defendants[2]
                                                    print(
                                                        f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                                    )
                                        except Exception as e:
                                            print(f"Error occurred while finding owner name parts: {e}")
                                            owner_name_parts = row['full_name'].split(",")
                                            if owner_name_parts >= 2:
                                                row['last_name'], row['first_name'] = owner_name_parts

                                    pprint(row) if row is not None else pprint("Row is None!!!")
                                    return row if row is not None else row
                                except Exception as e:
                                    print(f"Error processing {e}")

                            elif (
                                    not pd.isnull(row['property_street']) and row['property_street'].lower() not in [
                                'nan', '']
                            ):
                                county_name = WebDriverWait(row__, 120).until(EC.presence_of_element_located((By.XPATH,
                                                                                                              "//td[@class='x-grid3-col x-grid3-cell x-grid3-td-14 x-selectable ']/div[@class='x-grid3-cell-inner x-grid3-col-14']"))).text
                                if county_name.lower() == row['county'].lower():
                                    print(f"County Matched {row['county']} = {county_name}")
                                    WebDriverWait(row__, 120).until(EC.presence_of_element_located(
                                        (By.XPATH, "//a[normalize-space(text())='Property Details']"))).click()

                                    try:
                                        time.sleep(5)
                                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                                        just_value = row['assessed_value']

                                        if val:
                                            just_value_element = soup.find('td', text='Just Value:').find_next('td')
                                            just_value = just_value_element.get_text(strip=True)

                                            row['assessed_value'] = just_value

                                        if get_assessment:
                                            assessed_value_element = soup.find('td', text='Assessed Value:').find_next(
                                                'td')
                                            assessed_value = assessed_value_element.get_text(strip=True)

                                            row['assessed_value'] = assessed_value
                                            print(f"Assessed Value from get_assessment: {row['assessed_value']}")

                                        if get_address:
                                            owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                                            if "&amp;" in owner_name_element:
                                                owner_name_element = owner_name_element.replace('&amp;', '&')
                                            print(f"Owner Name ELEMENT => {owner_name_element}")
                                            # owner_name = owner_name_element.get_text(strip=True)
                                            if owner_name_element:
                                                row['full_name'] = owner_name_element
                                                print(f"Owner Name: {owner_name_element}")
                                            else:
                                                print("Owner Name Not Found!!!")
                                            mailing_address_element = soup.find('td', text='Mailing Address:')
                                            mailing_address = mailing_address_element.find_next('td').get_text(
                                                strip=True)
                                            if mailing_address:
                                                print(f"Mailing address => {mailing_address}")
                                                row['current_address'] = mailing_address
                                            else:
                                                print("Mailing Address Not Found!!!")

                                            defendants = []
                                            try:
                                                owner_name_parts = re.split(r'&|AND|\n', row['full_name'],
                                                                            flags=re.IGNORECASE)
                                                if len(owner_name_parts) >= 2:
                                                    for part in owner_name_parts:
                                                        split_ = part.split(",")
                                                        print(f"Part => {split_}")
                                                        defendants.extend(split_)
                                                    print(f"Defendants length => {len(defendants)}")
                                                    if len(defendants) >= 3:
                                                        row['full_name'] = defendants[0]
                                                        row['alternate_defendant_1'] = defendants[1]
                                                        row['alternate_defendant_2'] = defendants[2]
                                                        print(
                                                            f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                                        )
                                            except Exception as e:
                                                print(f"Error occurred while finding owner name parts: {e}")
                                                owner_name_parts = row['full_name'].split(",")
                                                if owner_name_parts >= 2:
                                                    row['last_name'], row['first_name'] = owner_name_parts

                                        pprint(row)
                                        return row
                                    except Exception as e:
                                        print(f"Error processing {e}")

                            else:
                                print(
                                    f"Parcel with id: {row['parcel_id']} not found => Parcel id = {row['parcel']}, pin = {pin_string}"
                                )


                        elif (
                                not pd.isnull(row['property_street']) and row['property_street'].lower() not in ['nan', '']
                        ):
                            county_name = WebDriverWait(row__, 120).until(EC.presence_of_element_located((By.XPATH,
                                                                                                          "//td[@class='x-grid3-col x-grid3-cell x-grid3-td-14 x-selectable ']/div[@class='x-grid3-cell-inner x-grid3-col-14']"))).text
                            if county_name.lower() == row['county'].lower():
                                print(f"County Matched {row['county']} = {county_name}")
                                WebDriverWait(row__, 120).until(EC.presence_of_element_located(
                                    (By.XPATH, "//a[normalize-space(text())='Property Details']"))).click()

                                try:
                                    time.sleep(5)
                                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    just_value = row['assessed_value']

                                    if val:
                                        just_value_element = soup.find('td', text='Just Value:').find_next('td')
                                        just_value = just_value_element.get_text(strip=True)

                                        row['assessed_value'] = just_value

                                    if get_assessment:
                                        assessed_value_element = soup.find('td', text='Assessed Value:').find_next('td')
                                        assessed_value = assessed_value_element.get_text(strip=True)

                                        row['assessed_value'] = assessed_value
                                        print(f"Assessed Value from get_assessment: {row['assessed_value']}")

                                    if get_address:
                                        owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                                        if "&amp;" in owner_name_element:
                                            owner_name_element = owner_name_element.replace('&amp;', '&')
                                        print(f"Owner Name ELEMENT => {owner_name_element}")
                                        # owner_name = owner_name_element.get_text(strip=True)
                                        if owner_name_element:
                                            row['full_name'] = owner_name_element
                                            print(f"Owner Name: {owner_name_element}")
                                        else:
                                            print("Owner Name Not Found!!!")

                                        mailing_address_element = soup.find('td', text='Mailing Address:')
                                        mailing_address = mailing_address_element.find_next('td').get_text(strip=True)
                                        if mailing_address:
                                            print(f"Mailing address => {mailing_address}")
                                            row['current_address'] = mailing_address
                                        else:
                                            print("Mailing Address Not Found!!!")

                                        defendants = []
                                        try:
                                            owner_name_parts = re.split(r'&|AND|\n', row['full_name'],
                                                                        flags=re.IGNORECASE)
                                            if len(owner_name_parts) >= 2:
                                                for part in owner_name_parts:
                                                    split_ = part.split(",")
                                                    print(f"Part => {split_}")
                                                    defendants.extend(split_)
                                                print(f"Defendants length => {len(defendants)}")
                                                if len(defendants) >= 3:
                                                    row['full_name'] = defendants[0]
                                                    row['alternate_defendant_1'] = defendants[1]
                                                    row['alternate_defendant_2'] = defendants[2]
                                                    print(
                                                        f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                                    )
                                        except Exception as e:
                                            print(f"Error occurred while finding owner name parts: {e}")
                                            owner_name_parts = row['full_name'].split(",")
                                            if owner_name_parts >= 2:
                                                row['last_name'], row['first_name'] = owner_name_parts
                                    pprint(row)
                                    return row
                                except Exception as e:
                                    print(f"Error processing {e}")
                    except:
                        print(f"No Match!!!")
            except Exception as e:
                print(f"Error processing {e}")
    except Exception as e:
        print(f"ERorr!!!! {e}")
        print(f"Invalid Parcel ID => {row['parcel_id']}")

        try:
            go_to_parcel(driver)
            search__ = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "formSearchAddress1")))
            search__.clear()
            parcel_input.clear()
            search__.send_keys(row['property_street'])
            search__.send_keys(Keys.ENTER)

            rows = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "x-grid3-row")))

            for row__ in rows:
                try:
                    if (
                            not pd.isnull(row['parcel_id']) and isinstance(row['parcel_id'], str)
                            and str(row['parcel_id']).lower() not in ["property appraiser", "timeshare", "",
                                                                      "multiple parcels",
                                                                      "multiple parcel", "nan"]
                    ):
                        print("In if Conditions")
                        numeric_string = ''.join(filter(str.isdigit, str(row['parcel_id'])))
                        print(f"Numeric string => {numeric_string}")
                        pin = WebDriverWait(row__, 120).until(EC.presence_of_element_located((By.XPATH,
                                                                                              "//td[@class='x-grid3-col x-grid3-cell x-grid3-td-3 x-selectable ']/div[@class='x-grid3-cell-inner x-grid3-col-3']"))).text

                        pin_string = ''.join(filter(str.isdigit, pin))
                        print(f"Pin string => {pin_string}")

                        if pin_string == numeric_string:
                            print(f"Found parcel with id: {row['parcel_id']}")
                            WebDriverWait(row__, 120).until(EC.presence_of_element_located(
                                (By.XPATH, "//a[normalize-space(text())='Property Details']"))).click()

                            try:
                                time.sleep(5)
                                soup = BeautifulSoup(driver.page_source, 'html.parser')
                                just_value = row['assessed_value']

                                if val:
                                    just_value_element = soup.find('td', text='Just Value:').find_next('td')
                                    just_value = just_value_element.get_text(strip=True)

                                    row['assessed_value'] = just_value

                                if get_assessment:
                                    assessed_value_element = soup.find('td', text='Assessed Value:').find_next('td')
                                    assessed_value = assessed_value_element.get_text(strip=True)

                                    row['assessed_value'] = assessed_value
                                    print(f"Assessed Value from get_assessment: {row['assessed_value']}")

                                if get_address:
                                    owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                                    if "&amp;" in owner_name_element:
                                        owner_name_element = owner_name_element.replace('&amp;', '&')
                                    print(f"Owner Name ELEMENT => {owner_name_element}")
                                    # owner_name = owner_name_element.get_text(strip=True)
                                    if owner_name_element:
                                        row['full_name'] = owner_name_element
                                        print(f"Owner Name: {owner_name_element}")
                                    else:
                                        print("Owner Name Not Found!!!")

                                    mailing_address_element = soup.find('td', text='Mailing Address:')
                                    mailing_address = mailing_address_element.find_next('td').get_text(strip=True)
                                    if mailing_address:
                                        print(f"Mailing address => {mailing_address}")
                                        row['current_address'] = mailing_address
                                    else:
                                        print("Mailing Address Not Found!!!")

                                    defendants = []
                                    try:
                                        owner_name_parts = re.split(r'&|AND|\n', row['full_name'], flags=re.IGNORECASE)
                                        pprint(owner_name_parts)
                                        if len(owner_name_parts) >= 2:
                                            for part in owner_name_parts:
                                                # Split each part by '&'
                                                split_ = part.split(",")
                                                print(f"Part => {split_}")
                                                defendants.extend(split_)
                                            print(f"Defendants length => {len(defendants)}")
                                            if len(defendants) >= 3:
                                                row['full_name'] = defendants[0]
                                                row['alternate_defendant_1'] = defendants[1]
                                                row['alternate_defendant_2'] = defendants[2]
                                                print(
                                                    f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                                )
                                    except Exception as e:
                                        print(f"Error occurred while finding owner name parts: {e}")
                                        owner_name_parts = row['full_name'].split(",")
                                        if owner_name_parts >= 2:
                                            row['last_name'], row['first_name'] = owner_name_parts

                                pprint(row)
                                return row
                            except Exception as e:
                                print(f"Error processing {e}")

                        elif (
                                row['property_street'] != "nan"
                        ):
                            county_name = WebDriverWait(row__, 120).until(EC.presence_of_element_located((By.XPATH,
                                                                                                          "//td[@class='x-grid3-col x-grid3-cell x-grid3-td-14 x-selectable ']/div[@class='x-grid3-cell-inner x-grid3-col-14']"))).text
                            if county_name.lower() == row['county'].lower():
                                print(f"County Matched {row['county']} = {county_name}")
                                WebDriverWait(row__, 120).until(EC.presence_of_element_located(
                                    (By.XPATH, "//a[normalize-space(text())='Property Details']"))).click()

                                try:
                                    time.sleep(5)
                                    soup = BeautifulSoup(driver.page_source, 'html.parser')

                                    just_value = row['assessed_value']

                                    if val:
                                        just_value_element = soup.find('td', text='Just Value:').find_next('td')
                                        just_value = just_value_element.get_text(strip=True)

                                        row['assessed_value'] = just_value

                                    if get_assessment:
                                        assessed_value_element = soup.find('td', text='Assessed Value:').find_next('td')
                                        assessed_value = assessed_value_element.get_text(strip=True)

                                        row['assessed_value'] = assessed_value
                                        print(f"Assessed Value from get_assessment: {row['assessed_value']}")

                                    if get_address:
                                        # Find "Owner Name" element
                                        owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                                        if "&amp;" in owner_name_element:
                                            owner_name_element = owner_name_element.replace('&amp;', '&')
                                        print(f"Owner Name ELEMENT => {owner_name_element}")
                                        # owner_name = owner_name_element.get_text(strip=True)
                                        if owner_name_element:
                                            row['full_name'] = owner_name_element
                                            print(f"Owner Name: {owner_name_element}")
                                        else:
                                            print("Owner Name Not Found!!!")

                                        mailing_address_element = soup.find('td', text='Mailing Address:')

                                        mailing_address = mailing_address_element.find_next('td').get_text(strip=True)
                                        if mailing_address:
                                            print(f"Mailing address => {mailing_address}")
                                            row['current_address'] = mailing_address
                                        else:
                                            print("Mailing Address Not Found!!!")

                                        defendants = []
                                        try:
                                            owner_name_parts = re.split(r'&|AND|\n', row['full_name'],
                                                                        flags=re.IGNORECASE)
                                            if len(owner_name_parts) >= 2:
                                                for part in owner_name_parts:
                                                    # Split each part by '&'
                                                    split_ = part.split(",")
                                                    print(f"Part => {split_}")
                                                    defendants.extend(split_)

                                                print(f"Defendants length => {len(defendants)}")
                                                if len(defendants) >= 3:
                                                    row['full_name'] = defendants[0]
                                                    row['alternate_defendant_1'] = defendants[1]
                                                    row['alternate_defendant_2'] = defendants[2]
                                                    print(
                                                        f"Full name => {row['full_name']}, alt_defendant_1 => {row['alternate_defendant_1']}, alt_defendant_2 => {row['alternate_defendant_2']}"
                                                    )
                                        except Exception as e:
                                            print(f"Error occurred while finding owner name parts: {e}")
                                            owner_name_parts = row['full_name'].split(",")
                                            if owner_name_parts >= 2:
                                                row['last_name'], row['first_name'] = owner_name_parts

                                    pprint(row)
                                    return row
                                except Exception as e:
                                    print(f"Error processing {e}")
                        else:
                            print(
                                f"Parcel with id: {row['parcel_id']} not found => Parcel id = {row['parcel']}, pin = {pin_string}"
                            )

                    elif (
                            row['property_street'] != "nan"
                    ):
                        county_name = WebDriverWait(row__, 120).until(EC.presence_of_element_located((By.XPATH,
                                                                                                      "//td[@class='x-grid3-col x-grid3-cell x-grid3-td-14 x-selectable ']/div[@class='x-grid3-cell-inner x-grid3-col-14']"))).text
                        if county_name.lower() == row['county'].lower():
                            print(f"County Matched {row['county']} = {county_name}")
                            WebDriverWait(row__, 120).until(EC.presence_of_element_located(
                                (By.XPATH, "//a[normalize-space(text())='Property Details']"))).click()

                            try:
                                time.sleep(5)
                                soup = BeautifulSoup(driver.page_source, 'html.parser')
                                # print(soup)

                                # Initialize variables
                                just_value = row['assessed_value']

                                if val:
                                    # Find "Just Value" element
                                    just_value_element = soup.find('td', text='Just Value:').find_next('td')
                                    just_value = just_value_element.get_text(strip=True)

                                    row['assessed_value'] = just_value

                                if get_assessment:
                                    # Find "Assessed Value" element
                                    assessed_value_element = soup.find('td', text='Assessed Value:').find_next('td')
                                    assessed_value = assessed_value_element.get_text(strip=True)

                                    row['assessed_value'] = assessed_value
                                    print(f"Assessed Value from get_assessment: {row['assessed_value']}")

                                if get_address:
                                    # Find "Owner Name" element
                                    owner_name_element = soup.find('td', string='Owner Name:').find_next('td').decode_contents().replace('<br/>', '\n').replace('<br>', '\n').strip()
                                    if "&amp;" in owner_name_element:
                                        owner_name_element = owner_name_element.replace('&amp;', '&')
                                    print(f"Owner Name ELEMENT => {owner_name_element}")
                                    # owner_name = owner_name_element.get_text(strip=True)
                                    if owner_name_element:
                                        row['full_name'] = owner_name_element
                                        print(f"Owner Name: {owner_name_element}")
                                    else:
                                        print("Owner Name Not Found!!!")

                                    # Find "Mailing Address" element
                                    mailing_address_element = soup.find('td', text='Mailing Address:')
                                    # print(f"Mailing element => {mailing_address_element.text}")

                                    mailing_address = mailing_address_element.find_next('td').get_text(strip=True)
                                    if mailing_address:
                                        print(f"Mailing address => {mailing_address}")
                                        row['current_address'] = mailing_address
                                    else:
                                        print("Mailing Address Not Found!!!")

                                    defendants = []
                                    try:
                                        owner_name_parts = re.split(r'&|AND|\n', row['full_name'], flags=re.IGNORECASE)
                                        pprint(owner_name_parts)
                                        if len(owner_name_parts) >= 2:
                                            for part in owner_name_parts:
                                                # Split each part by '&'
                                                split_ = part.split(",")
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
                                                # row['first_name'] = "nan"
                                                # row['last_name'] = "nan"
                                    except Exception as e:
                                        print(f"Error occurred while finding owner name parts: {e}")
                                        owner_name_parts = row['full_name'].split(",")
                                        if owner_name_parts >= 2:
                                            row['last_name'], row['first_name'] = owner_name_parts

                                pprint(row)
                                return row
                            except Exception as e:
                                print(f"Error processing {e}")
                    else:
                        print(
                            f"Neither Street ({row['property_street']}) nor Parcel ID ({row['parcel_id']} is available")
                except:
                    print(f"No Match!!!")
        except Exception as e:
            print(f"Error processing {e}")

#
# if __name__ == "__main__":
#     driver = bot_setup()
#     processed_data = pd.read_csv("test2.csv")
#     search(driver)
#     # Initialize an empty list to store modified rows
#     modified_rows = []
#
#     # Iterate over rows in the processed_data DataFrame
#     for index, row in processed_data.iterrows():
#         # Convert the entire row to string
#         row_str = {key: str(value) for key, value in row.items()}
#
#         # # Print data types for verification
#         # print("Data type of row['parcel_id']: ", type(row_str['parcel_id']))
#         # print("Data type of row['county']: ", type(row_str['county']))
#         # print("Data type of row['property_street']: ", type(row_str['property_street']))
#         # print("Data type of row['full_name']: ", type(row_str['full_name']))
#         # print("Data type of row['current_address']: ", type(row_str['current_address']))
#         # print("Data type of row['assessed_value']: ", type(row_str['assessed_value']))
#
#         # Call the map_main function to process the row
#         new_row = map_main(driver, row_str)
#
#         if new_row:
#             # Append the modified row to the list
#             modified_rows.append(new_row)
#             print("------------------------------------------------------------------------------------------------")
#             pprint(new_row)
#         else:
#             modified_rows.append(row_str)
#
#     # Convert the list of modified rows to a DataFrame
#     modified_df = pd.DataFrame(modified_rows)
#
#     # Save the modified DataFrame to a new CSV file
#     modified_df.to_csv("testing\modified_data.csv", index=False)
