from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

import json
import time
import sched
import smtplib


schedule = None
appSettings = None
permitAvail = {}

def main():
    """
    Gets information from files and begins scheduling permit checks.
    Runs a permit check immediately.
    """
    global appSettings
    global schedule
    global permitAvail


    # Get settings
    try:
        with open("settings.json", "r") as settingsFile:
            appSettings = json.load(settingsFile)
    except Exception as err:
        print(f"ERROR: Failed to load settings with error: {err}")
        print("NOTICE: Make sure that settings.json exists and is properly formatted.")
        quit(1)

    # Get previous availability
    try:
        with open("permitAvail.json", "r") as permitAvailFile:
            permitAvail = json.load(permitAvailFile)
    except Exception as err:
        print(f"ERROR: Failed to load previously found permits with error: {err}")
        print("NOTICE: Assuming no permits previously found.")

    # Validate appSettings
    validate_app_settings()

    schedule = sched.scheduler(time.time, time.sleep)

    schedule_checking(True) # True to run immediately once
    schedule.run()

def validate_app_settings():
    """
    Validates that settings.json had the approriate information.
    """
    global appSettings
    
    # Default "show-browser" to False
    if "show-browser" not in appSettings:
        print('NOTICE: No "show-browser" field in settings.json. Using false as a default.')
        appSettings["show-browser"] = False

    # Default "run-once" to False
    if "run-once" not in appSettings:
        print('NOTICE: No "run-once" field in settings.json. Using true as a default.')
        appSettings["run-once"] = False

    # Default "run-every" to 15 minutes
    if "run-every" not in appSettings:
        print('NOTICE: No "run-every" field in settings.json. Using 15 (minutes) as a default.')
        appSettings["run-every"] = 15 * 60

    # Default "wait-for-load" to 2 seconds
    if "wait-for-load" not in appSettings:
        print('NOTICE: No "wait-for-load" field in settings.json. Using 2 (seconds) as a default.')
        appSettings["wait-for-load"] = 2

    # Handle no permits
    if "permits" not in appSettings:
        print('NOTICE: No "permits" field in settings.json. No permits to search for. Closing program.')
        quit(1)
    elif len(appSettings["permits"]) == 0:
        print('NOTICE: Empty list of permits in settings.json. No permits to search for. Closing program.')
        quit(1)
    # TODO handle permit format

    # Handle Dates
    if "dates" not in appSettings:
        print('NOTICE: No "dates" field in settings.json. No time range to search in. Closing program.')
        quit(1)
    elif "start" not in appSettings["dates"] or "end" not in appSettings["dates"]:
        print('NOTICE: Must have "start" and "end" fields under "dates" in settings.json. No time range to search in. Closing program.')
        quit(1)
    # TODO handle date format ("MONTH YYYY")

    # TODO check emails

def schedule_checking(runNow = False):
    """
    Schedules a task to check for permits.
    If the given parameter is true, the task is run immediately.
    Else, it is run in "run-every" seconds defined in settings.json.
    """
    global appSettings
    global schedule

    try:
        runIn = 0 if runNow else appSettings["run-every"]
        schedule.enter(runIn, 1, safe_check_for_permits)
    except Exception as err:
        print(f"ERROR: Failed to schedule permit checking with error {err}")

def safe_check_for_permits():
    """
    Wraps check_for_permits() call in a try catch to make sure the program doesn't crash.
    """

    try:
        check_for_permits()
    except Exception as err:
        print(f"ERROR: Error checking for permits ({err})")
        
        # Send email with error message
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            errorEmailBody = f"There was an error checking for permits at {timestamp}. The error message given is: {err}.\n\n"
            send_email("RECREATION BOT: Error checking for permits", errorEmailBody, True)
        except Exception as _:
            print("ERROR: Failed to send error email.")
            
        # Schedule another search for permits
        if not appSettings['run-once']:
            schedule_checking()

def check_for_permits():
    """
    Scrapes the appropriate recreation.gov sites to find permit availability.
    """
    global appSettings

    # Set browser options
    options = Options()

    if not appSettings["show-browser"]:
        options.add_argument("--headless")

    options.add_argument("--window-size=1920x1080")

    # Open Browser
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(appSettings["wait-for-load"])

    permitsToCheck = appSettings["permits"]
    foundPermitAvail = {}

    startMonth, startYear = appSettings["dates"]["start"].lower().split(" ")
    endMonth, endYear = appSettings["dates"]["end"].lower().split(" ")

    # Print that the search is starting with a timestamp
    print(f"\n\n----- {time.strftime('%Y-%m-%d %H:%M:%S')}: STARTING SEARCH FOR PERMIT AVAILABILITY -----")

    # Check all permits
    for permitToCheck in permitsToCheck:

        permitID = permitToCheck["id"]

        url = f"https://www.recreation.gov/permits/{permitID}"
        driver.get(url)
        foundPermitAvail[permitID] = {
            "url": url
        }

        # Get permit name
        name = driver.find_element(By.XPATH, '//*[@id="page-content"]/div/div[2]/div/div/div[1]/div[1]/h1').text
        foundPermitAvail[permitID]["name"] = name
        print(f'PERMITS:\tSearching for "{name}" permits')

        # Check for segment input
        segmentInput = None
        try:
            segmentInput = Select(driver.find_element(By.ID, "division-selection"))
        except NoSuchElementException:
            pass


        # Select 
        for segment in permitToCheck["segments"]:
            print(f'PERMITS:\t\tSearching for "{name}" -> "{segment}" permits')
            
            # Select segment and set num people
            if segmentInput is not None:
                # Select segment
                segmentInput.select_by_visible_text(segment)

                # Input people
                numPeopleInput = None
                try:
                    numPeopleInput = driver.find_element(By.ID, "number-input-")
                    # Ensure that the input has the right number of people
                    while not numPeopleInput.get_attribute('value') == str(permitToCheck["num-people"]):
                        numPeopleInput.clear()
                        numPeopleInput.send_keys(permitToCheck["num-people"])
                        numPeopleInput.send_keys(Keys.RETURN)
                except NoSuchElementException:
                    pass

            permitAvail = get_availability(driver, startMonth, startYear, endMonth, endYear)
            
            # Init segment list if needed
            if "segments" not in foundPermitAvail[permitID]:
                foundPermitAvail[permitID]["segments"] = {}

            # Add segment avail to list
            foundPermitAvail[permitID]["segments"][segment] = permitAvail

            print(f'PERMITS:\t\tDone searching for "{name}" -> "{segment}" permits')

        # Add permit avail
        if len(permitToCheck["segments"]) == 0:
            permitAvail = get_availability(driver, startMonth, startYear, endMonth, endYear)

            foundPermitAvail[permitID]["availability"] = permitAvail
            
        print(f'PERMITS:\tDone searching for "{name}" permits')

    compare_availability(foundPermitAvail)

    # Schedule another search for permits
    if not appSettings['run-once']:
        schedule_checking()


def get_availability(driver, startMonth, startYear, endMonth, endYear):
    """
    Gets the availability off of the current page and returns in.
    This changes the selected month to the starting one and then traverses to the end month.
    """

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

def compare_availability(foundPermitAvail):
    """
    Compares given permit availability with previously found permit
    availability. If there is new availability, a notification email
    is sent.
    """
    global permitAvail
    global appSettings

    newAvail = {}

    # Compare all permits
    for permit in appSettings["permits"]:
        foundAvail = foundPermitAvail[permit["id"]]

        # First time finding permit
        if permit["id"] not in permitAvail:
            continue

        oldAvail = permitAvail[permit["id"]]

        # Compare segmented permit avail
        if "segments" in foundAvail:
            for segment in foundAvail["segments"]:

                # First time finding segment
                if segment not in oldAvail["segments"]:
                    continue

                # Go over each month
                for month in foundAvail["segments"][segment]:

                    # First time finding this month for this segment
                    if month not in oldAvail["segments"][segment]:
                        continue

                    foundDaysAvail = foundAvail["segments"][segment][month]
                    oldDaysAvail = oldAvail["segments"][segment][month]

                    newDaysAvail = list(set(foundDaysAvail) - set(oldDaysAvail))

                    # Store new availability
                    if len(newDaysAvail) > 0:

                        # Init permit if needed
                        if permit["id"] not in newAvail:
                            newAvail[permit["id"]] = {}

                        # Init segments if needed
                        if "segments" not in newAvail[permit["id"]]:
                            newAvail[permit["id"]]["segments"] = {}

                        # Init specific segment if needed
                        if segment not in newAvail[permit["id"]]["segments"]:
                            newAvail[permit["id"]]["segments"][segment] = {}

                        newAvail[permit["id"]]["segments"][segment][month] = newDaysAvail
                        newAvail[permit["id"]]["name"] = foundAvail["name"]
                        newAvail[permit["id"]]["url"] = foundAvail["url"]

        # Compare permit avail
        else:
            for month in foundAvail["availability"]:

                # First time finding this month for this permit
                if month not in oldAvail["availability"]:
                    continue

                foundDaysAvail = foundAvail["availability"][month]
                oldDaysAvail = oldAvail["availability"][month]

                newDaysAvail = list(set(foundDaysAvail) - set(oldDaysAvail))
                
                # Store new availability
                if len(newDaysAvail) > 0:

                    # Init permit if needed
                    if permit["id"] not in newAvail:
                        newAvail[permit["id"]] = {}

                    # Init segments if needed
                    if "availability" not in newAvail[permit["id"]]:
                        newAvail[permit["id"]]["availability"] = {}

                    newAvail[permit["id"]]["availability"][month] = newDaysAvail
                    newAvail[permit["id"]]["name"] = foundAvail["name"]
                    newAvail[permit["id"]]["url"] = foundAvail["url"]

    # Notify
    if len(newAvail) > 0:
        notify_of_permits(newAvail)

    # Update
    permitAvail = foundPermitAvail
    with open("permitAvail.json", "w") as permitAvailFile:
        json.dump(permitAvail, permitAvailFile)
        print("FILES: Updated permitAvail.json")
        

def notify_of_permits(newAvail):
    """Sends an email notifying of the new availabilities given in the parameter."""
    global appSettings

    print(f"IMPORTANT: New availability found!!!! {newAvail}")

    # Format Email Body
    emailBody = ""
    for permitID in newAvail:
        name = newAvail[permitID]["name"]

        emailBody += f"{name} ({newAvail[permitID]['url']})\n"

        if "segments" in newAvail[permitID]:
            for segment in newAvail[permitID]["segments"]:
                emailBody += f"\t{segment}\n"

                for month in newAvail[permitID]["segments"][segment]:    
                    newDays = newAvail[permitID]["segments"][segment][month]
                    emailBody += f"\t\t{month}\n\t\t\t{newDays}\n"

        else:
            for month in newAvail[permitID]["availability"]:
                
                newDays = newAvail[permitID]["availability"][month]
                emailBody += f"\t{month}\n\t\t{newDays}\n"


    # Send email
    send_email("RECREATION BOT: New permit availability found", emailBody)


# Send an email with the given subject and body.
# The email is sent to/from the email(s) specified in the appSettings.
def send_email(subject, body, isError = False):
    """Sends an email with the given message."""
    global appSettings

    # Get emails
    fromEmail = appSettings["emails"]["sendFrom"]["email"]
    fromPass = appSettings["emails"]["sendFrom"]["appPass"]
    sendTo = appSettings["emails"]["sendTo"]

    if isError:
        sendTo = appSettings["emails"]["sendErrorsTo"]
    
    # Format email message
    emailText = f"From: {fromEmail}\r\n"
    emailText += f"To: {', '.join(sendTo)}\r\n"
    emailText += f"Subject: {subject}\r\n\r\n"
    emailText += f"{body}"

    try:
        emailServer = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        emailServer.ehlo()
        emailServer.login(fromEmail, fromPass)
        emailServer.sendmail(fromEmail, sendTo, emailText)
        emailServer.close()
        print("NOTIF: Email sent")
    except Exception as err:
        print(f"ERROR: Error sending email ({err})")

if __name__ == "__main__":
    main()