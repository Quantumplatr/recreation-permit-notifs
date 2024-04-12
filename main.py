from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

import json
import time
from datetime import datetime
import sched
import smtplib
import requests


schedule = None
app_settings = None
permit_avail = {}


def main():
    """
    Gets information from files and begins scheduling permit checks.
    Runs a permit check immediately.
    """
    global app_settings
    global schedule
    global permit_avail

    # Get settings
    try:
        with open("settings.json", "r") as settings_file:
            app_settings = json.load(settings_file)
    except Exception as err:
        print(f"ERROR: Failed to load settings with error: {err}")
        print("NOTICE: Make sure that settings.json exists and is properly formatted.")
        quit(1)

    # Get previous availability
    try:
        with open("permitAvail.json", "r") as permit_avail_file:
            permit_avail = json.load(permit_avail_file)
    except Exception as err:
        print(f"ERROR: Failed to load previously found permits with error: {err}")
        print("NOTICE: Assuming no permits previously found.")

    # Validate appSettings
    validate_app_settings()

    schedule = sched.scheduler(time.time, time.sleep)

    schedule_checking(True)  # True to run immediately once
    schedule.run()


def validate_app_settings():
    """
    Validates that settings.json had the approriate information.
    """
    global app_settings

    # Default "show-browser" to False
    if "show-browser" not in app_settings:
        print(
            'NOTICE: No "show-browser" field in settings.json. Using false as a default.'
        )
        app_settings["show-browser"] = False

    # Default "run-once" to False
    if "run-once" not in app_settings:
        print('NOTICE: No "run-once" field in settings.json. Using true as a default.')
        app_settings["run-once"] = False

    # Default "run-every" to 15 minutes
    if "run-every" not in app_settings:
        print(
            'NOTICE: No "run-every" field in settings.json. Using 15 (minutes) as a default.'
        )
        app_settings["run-every"] = 15 * 60

    # Handle no permits
    if "permits" not in app_settings:
        print(
            'NOTICE: No "permits" field in settings.json. No permits to search for. Closing program.'
        )
        quit(1)
    elif len(app_settings["permits"]) == 0:
        print(
            "NOTICE: Empty list of permits in settings.json. No permits to search for. Closing program."
        )
        quit(1)
    # TODO handle permit format

    # Handle Dates
    if "dates" not in app_settings:
        print(
            'NOTICE: No "dates" field in settings.json. No time range to search in. Closing program.'
        )
        quit(1)
    elif "start" not in app_settings["dates"] or "end" not in app_settings["dates"]:
        print(
            'NOTICE: Must have "start" and "end" fields under "dates" in settings.json. No time range to search in. Closing program.'
        )
        quit(1)
    # TODO handle date format ("MONTH YYYY")

    # TODO check emails


def schedule_checking(runNow=False):
    """
    Schedules a task to check for permits.
    If the given parameter is true, the task is run immediately.
    Else, it is run in "run-every" seconds defined in settings.json.
    """
    global app_settings
    global schedule

    try:
        runIn = 0 if runNow else app_settings["run-every"]
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
            send_email(
                "RECREATION BOT: Error checking for permits", errorEmailBody, True
            )
        except Exception as _:
            print("ERROR: Failed to send error email.")

        # Schedule another search for permits
        if not app_settings["run-once"]:
            schedule_checking()


def get_details_from_api(permit_id) -> dict:
    """
    Accesses the Recreation.gov API to get permit details for the given permit ID.
    Returns the details as a dictionary.
    """

    url = f"https://www.recreation.gov/api/permits/{permit_id}/details"
    response = requests.get(
        url,
        params={},
        headers={
            # User Agent to make request work
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        },
    )

    if response.status_code != 200:
        print(f"ERROR: Failed to get details for permit {permit_id}.")
        return None

    return response.json()["payload"]


def get_availability_from_api(permit_id, division_id) -> dict:
    """
    Accesses the Recreation.gov API to get permit availability for the given permit and division IDs.
    """

    global app_settings

    # Get start and end dates
    start_date = app_settings["dates"]["start"]
    end_date = app_settings["dates"]["end"]

    # Format dates
    start_date = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").isoformat()

    # Note that query params must be in UTC time ISO format (end in Z)
    # Example: 2022-01-01T00:00:00Z
    # This is done in the URL not in the params to avoid encoding issues
    url = f"https://www.recreation.gov/api/permits/{permit_id}/divisions/{division_id}/availability?start_date={start_date}Z&end_date={end_date}Z"
    response = requests.get(
        url,
        headers={
            # User Agent to make request work
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
        },
    )

    if response.status_code != 200:
        print(
            f"ERROR: Failed to get availability for permit {permit_id} and division {division_id}."
        )
        return None

    return response.json()["payload"]


def check_for_permits():
    """
    Accesses the API to get permit availability.
    """
    global app_settings

    permits_to_check = app_settings["permits"]
    found_permit_avail = {}

    # Check all permits
    for permit in permits_to_check:
        permit_id = permit["id"]

        details = get_details_from_api(permit_id)

        # Set up permit in found permit availability
        found_permit_avail[permit_id] = {
            "name": details["name"],
            "url": f"https://www.recreation.gov/permits/{permit_id}",
        }

        # If details are not found, skip this permit
        if details is None:
            continue

        # TODO:  report error / send email?

        # Get divisions to check
        # If no segments, get first division
        # If segments, get all divisions
        divisions = {}
        if "segments" in permit and len(permit["segments"]) > 0:
            division_names = permit["segments"]

            # Get division ids from details
            for division_id, division in details["divisions"].items():
                if division["name"] in division_names:
                    divisions[division_id] = division["name"]

        else:
            divisions[next(iter(details["divisions"]))] = None

        # Get availability for each division
        for division_id, division_name in divisions.items():
            avail_data = get_availability_from_api(permit_id, division_id)

            # If availability is not found, skip this division
            if avail_data is None:
                continue

            # TODO: report error / send email?

            # Set up segment in found permit availability
            if division_name is None:
                found_permit_avail[permit_id]["availability"] = {}
            else:
                if "segments" not in found_permit_avail[permit_id]:
                    found_permit_avail[permit_id]["segments"] = {}
                
                found_permit_avail[permit_id]["segments"][division_name] = {}

            # Iterate over days to check for availability
            for day, avail_info in avail_data["date_availability"].items():
                if avail_info["remaining"] > 0:
                    # Get date in format "MONTH YEAR" from ISO date
                    date = datetime.strptime(day, "%Y-%m-%dT%H:%M:%S%z")
                    
                    day = int(date.strftime("%d"))
                    month_year = date.strftime("%B %Y")
                    
                    # Add day to availability
                    if division_name is None:
                        if month_year not in found_permit_avail[permit_id]["availability"]:
                            found_permit_avail[permit_id]["availability"][month_year] = []
                        
                        found_permit_avail[permit_id]["availability"][month_year].append(day)
                    else:
                        if month_year not in found_permit_avail[permit_id]["segments"][division_name]:
                            found_permit_avail[permit_id]["segments"][division_name][month_year] = []
                            
                        found_permit_avail[permit_id]["segments"][division_name][month_year].append(day)
    
    compare_availability(found_permit_avail)
    
    if not app_settings["run-once"]:
        schedule_checking()


def compare_availability(found_permit_avail):
    """
    Compares given permit availability with previously found permit
    availability. If there is new availability, a notification email
    is sent.
    """
    global permit_avail
    global app_settings

    newAvail = {}

    # Compare all permits
    for permit in app_settings["permits"]:
        foundAvail = found_permit_avail[permit["id"]]

        # First time finding permit
        if permit["id"] not in permit_avail:
            continue

        oldAvail = permit_avail[permit["id"]]

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

                        newAvail[permit["id"]]["segments"][segment][month] = (
                            newDaysAvail
                        )
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
    permit_avail = found_permit_avail
    with open("permitAvail.json", "w") as permitAvailFile:
        json.dump(permit_avail, permitAvailFile)
        print("FILES: Updated permitAvail.json")


def notify_of_permits(newAvail):
    """Sends an email notifying of the new availabilities given in the parameter."""
    global app_settings

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
    today = datetime.now()
    send_email(f"RECREATION BOT: New permit availability found as of {today.isoformat()}", emailBody)


# Send an email with the given subject and body.
# The email is sent to/from the email(s) specified in the appSettings.
def send_email(subject, body, isError=False):
    """Sends an email with the given message."""
    global app_settings

    # Get emails
    fromEmail = app_settings["emails"]["sendFrom"]["email"]
    fromPass = app_settings["emails"]["sendFrom"]["appPass"]
    sendTo = app_settings["emails"]["sendTo"]

    if isError:
        sendTo = app_settings["emails"]["sendErrorsTo"]

    # Format email message
    emailText = f"From: {fromEmail}\r\n"
    emailText += f"To: {', '.join(sendTo)}\r\n"
    emailText += f"Subject: {subject}\r\n\r\n"
    emailText += f"{body}"

    try:
        emailServer = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        emailServer.ehlo()
        emailServer.login(fromEmail, fromPass)
        emailServer.sendmail(fromEmail, sendTo, emailText)
        emailServer.close()
        print("NOTIF: Email sent")
    except Exception as err:
        print(f"ERROR: Error sending email ({err})")


if __name__ == "__main__":
    main()
