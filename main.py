from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

import json
import time
import sched


schedule = None
appSettings = None
permitAvailability = None

def main():
    """TODO comment""" # TODO comment
    global appSettings
    global schedule

    try:
        with open("settings.json", "r") as settingsFile:
            appSettings = json.load(settingsFile)
    except Exception as err:
        print(f"ERROR: Failed to load settings with error: {err}")
        print("NOTICE: Make sure that settings.json exists and is properly formatted.")
        quit(1)

    # Validate appSettings
    validate_app_settings()

    schedule = sched.scheduler(time.time, time.sleep)

    schedule_checking(True) # True to run immediately once
    schedule.run()

def validate_app_settings():
    """TODO comment""" # TODO comment
    global appSettings
    
    # Default "show-browser" to False
    if not "show-browser" in appSettings:
        print('NOTICE: No "show-browser" field in settings.json. Using false as a default.')
        appSettings["show-browser"] = False

    # Default "run-once" to False
    if not "run-once" in appSettings:
        print('NOTICE: No "run-once" field in settings.json. Using true as a default.')
        appSettings["run-once"] = False

    # Default "run-every" to 15 minutes
    if not "run-every" in appSettings:
        print('NOTICE: No "run-every" field in settings.json. Using 15 (minutes) as a default.')
        appSettings["run-every"] = 15 * 60

    # Default "wait-for-load" to 2 seconds
    if not "wait-for-load" in appSettings:
        print('NOTICE: No "wait-for-load" field in settings.json. Using 2 (seconds) as a default.')
        appSettings["wait-for-load"] = 2

    # Handle no permits
    if not "permits" in appSettings:
        print('NOTICE: No "permits" field in settings.json. No permits to search for. Closing program.')
        quit(1)
    elif len(appSettings["permits"]) == 0:
        print('NOTICE: Empty list of permits in settings.json. No permits to search for. Closing program.')
        quit(1)
    # TODO handle permit format

    # Handle Dates
    if not "dates" in appSettings:
        print('NOTICE: No "dates" field in settings.json. No time range to search in. Closing program.')
        quit(1)
    elif not "start" in appSettings["dates"] or not "end" in appSettings["dates"]:
        print('NOTICE: Must have "start" and "end" fields under "dates" in settings.json. No time range to search in. Closing program.')
        quit(1)
    # TODO handle date format ("MONTH YYYY")

    # TODO check emails

def schedule_checking(runNow = False):
    """TODO comment""" # TODO comment
    global appSettings
    global schedule

    try:
        runIn = 0 if runNow else appSettings["run-every"]
        schedule.enter(runIn, 1, check_for_permits)
    except Exception as err:
        print(f"ERROR: Failed to schedule permit checking with error {err}")

def check_for_permits():
    """TODO comment""" # TODO comment
    global appSettings

    # Set browser options
    options = Options()

    if not appSettings["show-browser"]:
        options.add_argument("--headless")

    options.add_argument("--window-size=1920x1080")
    # options.add_experimental_option("detach", True)


    # Open Browser
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(appSettings["wait-for-load"])

    permitsToCheck = appSettings["permits"]
    foundPermitAvail = {}

    startMonth, startYear = appSettings["dates"]["start"].lower().split(" ")
    endMonth, endYear = appSettings["dates"]["end"].lower().split(" ")

    # startYear = int(startYear)
    # endYear = int(endYear)

    for permitToCheck in permitsToCheck:

        permitID = permitToCheck["id"]

        driver.get(f"https://www.recreation.gov/permits/{permitID}")

        # TODO check for segments
        segmentInput = None
        try:
            segmentInput = Select(driver.find_element(By.ID, "division-selection"))
        except NoSuchElementException as err:
            pass


        # Select 
        for segment in permitToCheck["segments"]:
            
            # Select segment and set num people
            if segmentInput != None:
                # Select segment
                segmentInput.select_by_visible_text(segment)

                time.sleep(1) # TODO delete me

                # Input people
                numPeopleInput = None
                try:
                    numPeopleInput = driver.find_element(By.ID, "number-input-")
                    numPeopleInput.clear()
                    numPeopleInput.send_keys(permitToCheck["num-people"])
                    numPeopleInput.send_keys(Keys.RETURN)
                except NoSuchElementException as err:
                    pass

            permitAvail = get_availability(driver, startMonth, startYear, endMonth, endYear)
            print(f'availability for {permitID} -> {segment}')
            print(permitAvail)

        if len(permitToCheck["segments"]) == 0:
            permitAvail = get_availability(driver, startMonth, startYear, endMonth, endYear)

            print(f'availability for {permitID}')
            print(permitAvail)


        time.sleep(3)

    # Check for permits
    if not appSettings['run-once']:
        schedule_checking()


    # TODO delete me
    # driver.get_screenshot_as_file("capture.png")
    # print("Hello World")


def get_availability(driver, startMonth, startYear, endMonth, endYear):
    selectedMonthElem = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[2]/div/div[2]/div/div/strong')
    selectedMonth, selectedYear = selectedMonthElem.text.lower().split(" ")
    
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

    goPrevMonth = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[1]/div[1]/div')
    goNextMonth = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[1]/div[2]/div')

    availability = {}

    # Go to the right year
    while selectedYear != startYear:

        # Navigate
        if selectedYear > startYear:
            goPrevMonth.click()
        else:
            goNextMonth.click()
        
        # Get new month
        selectedMonthElem = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[2]/div/div[2]/div/div/strong')
        selectedMonthElemText = selectedMonthElem.text.lower()
        while selectedMonthElemText == "":
            selectedMonthElem = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[2]/div/div[2]/div/div/strong')
            selectedMonthElemText = selectedMonthElem.text.lower()
            time.sleep(0.1)

        selectedMonth, selectedYear = selectedMonthElemText.split(" ")

    # Go to the right month
    while months.index(selectedMonth) != months.index(startMonth):
        
        # Navigate
        if months.index(selectedMonth) > months.index(startMonth):
            goPrevMonth.click()
        else:
            goNextMonth.click()
        
        # Get new month
        selectedMonthElem = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[2]/div/div[2]/div/div/strong')
        selectedMonthElemText = selectedMonthElem.text.lower()
        while selectedMonthElemText == "":
            selectedMonthElem = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[2]/div/div[2]/div/div/strong')
            selectedMonthElemText = selectedMonthElem.text.lower()
            time.sleep(0.1)

        selectedMonth, selectedYear = selectedMonthElemText.split(" ")

    #  Go through months
    while selectedYear <= endYear:
        while months.index(selectedMonth) <= months.index(endMonth):

            # Get availability
            availableDays = driver.find_elements(By.CLASS_NAME, "rec-available-day")
            dayNums = []
            for availableDay in availableDays:
                # Get day text and add to list
                dayNum = availableDay.find_element(By.XPATH, "div[1]").text
                if dayNum != "":
                    dayNums.append(int(dayNum)) 
            availability[f"{selectedMonth.capitalize()} {selectedYear}"] = dayNums

            # Go to next month
            goNextMonth.click()
            time.sleep(1)

            # Get new month year
            selectedMonthElem = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div[2]/div/div[2]/div/div/strong')
            selectedMonth, selectedYear = selectedMonthElem.text.lower().split(" ")
        
        # Done
        if selectedYear == endYear:
            break

    return availability

def notify_of_permits():
    """TODO comment""" # TODO comment
    global appSettings


if __name__ == "__main__":
    main()