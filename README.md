# Recreation Permit Notifs

## Table of Contents
- [Recreation Permit Notifs](#recreation-permit-notifs)
  - [Table of Contents](#table-of-contents)
  - [1. Install](#1-install)
    - [1.1 Get Python](#11-get-python)
    - [1.2 Dependencies](#12-dependencies)
      - [1.2.1 Pipenv](#121-pipenv)
  - [2. Running](#2-running)
    - [2.1 Settings](#21-settings)
    - [2.2 Running The Code](#22-running-the-code)
    - [2.3 Testing The Code](#23-testing-the-code)
    - [2.4 Output Of The Code](#24-output-of-the-code)
      - [2.4.1 Console Output](#241-console-output)
      - [2.4.2 File Output](#242-file-output)

## 1. Install

### 1.1 Get Python
Make sure you have [Python](https://www.python.org/downloads/) installed. This was developed using Python 3.9.0.
You can check your `python` version with:
```bash
python --version
```

### 1.2 Dependencies
#### 1.2.1 Pipenv
Make sure you have `pipenv`. You can check your version of `pipenv` with:
```bash
pipenv --version
```

To install `pipenv`, run:
```bash
python -m pip install pipenv
```

## 2. Running
### 2.1 Settings
Settings are defined in [settings.json](settings.json). 
Below is the default settings:
```JSON
{
    "emails": {
        "sendFrom": {
            "email": "recreation.permit.bot@gmail.com",
            "pass": "RecreationPermitPass1"
        },
        "sendTo": ["email@example.com"]
    },
    "dates": {
        "start": "May 2022",
        "end": "September 2022"
    },
    "run-every": 60,
    "run-once": false,
    "permits": [{
        "id": "234622",
        "segments": [],
        "num-people": -1
    }, {
        "id": "250014",
        "segments": ["Deerlodge Park, Yampa River", "Gates of Lodore, Green River"],
        "num-people": -1
    }, {
        "id": "250986",
        "segments": ["Sand Island to Clay Hills", "Mexican Hat to Clay Hills"],
        "num-people": 10
    }, {
        "id": "234623",
        "segments": [],
        "num-people": -1
    }, {
        "id": "234624",
        "segments": [],
        "num-people": -1
    }, {
        "id": "234625",
        "segments": [],
        "num-people": -1
    }]
}
```

Below is the description of these settings. 
**NOTE: the format of these fields is important and the program may not work if they are formatted improperly.**

- `emails`
  - `sendFrom`
    - `email`
      - Email to send notifications from. `recreation.permit.bot@gmail.com` should work. Note that this requires "Less Secure Apps" enabled so it is good to have this is a dedicated email for security.
    - `pass`
      - Password for the email to send from. `RecreationPermitPass1` is what I have set it to. Again, for best security practice it is good to not store important passwords in a file.
  - `sendTo`
    - List of emails to send to
    - Format: `["email1@example.com","email2@example.com"]`
- `dates`
  - `start`
    - Beginning of date range to search from
    - Format: `YYYY-MM-DD` (e.g. `2024-04-01`)
      - This is strict
  - `end`
    - End of date range to search from
    - Format: `YYYY-MM-DD` (e.g. `2024-04-01`)
      - This is strict
- `run-every`
  - Tells the program how often (in seconds) to check for permits.
  - Note that this is the delay between the end of one check and the start of the next.
  - Format: `number` (e.g. `10`, `60`, `600`)
- `run-once`
  - Values: `true` or `false`
  - If `true`, permits will be checked for once and not 
- `permits`
  - The permits to search for.
  - `id`
    - The `id` of the permit to search for.
    - This can be found in the URL of a permit's page. For example, the URL of "Dinosaur Green And Yampa River Permits" is [https://www.recreation.gov/permits/250014](https://www.recreation.gov/permits/250014) so the `id` is `"250014"`.
    - Format: `"<id>"` (e.g. `"250014"`)
  - `segments`
    - List of segment names for the permit. These segments are found (if they exist) above the calendar on the permit's page.
    - **NOTE: This text must be exact if there are segments.**
    - Format: `["Segment1","Segment2"]`
      - If there are no segments for the permit, the value should be `[]` to indicate that there are none.
  - `num-people`
    - The amount of people input to the "Group Members" input if it exists.
    - Format: `number` (e.g. `5`, `10`)
      - If there is no need to input this, `-1` is a good value however it doesn't matter.

### 2.2 Running The Code
Simply run `main.py` with `pipenv`:

```bash
pipenv run python main.py
```

Running this with `pipenv` will ensure that dependencies are installed and will set up a virtual environment for the code to run in. To close the program, close your shell or input `CTRL+c`.

### 2.3 Testing The Code
A good way to test the code is to set `show-browser` and `run-once` to `true`.
Running it once will populate `permitAvail.json` with the permits it finds.
Assuming some availabilities were found, remove a *day* from `permitAvail.json`.
**Be careful that you do not ruin the syntax (days are comma separated and the last day is not followed by a comma).**
Running it again will notice this change in availability and should send an email about it.

### 2.4 Output Of The Code
#### 2.4.1 Console Output
The console will have output telling what the program is doing. Any output from this code will be of the format `<TYPE>: <msg>` (e.g. `PERMITS: Starting Search for Permit Availability`). Other output is likely messages from the web scraper used in this code or error messages. If there are error messages, there is likely something wrong with the code so it is good to forward those errors to me when you see them.

#### 2.4.2 File Output
Permit availability is stored in [permitAvail.json](permitAvail.json). There is not much need to edit this. It is fairly human readable. If there are issues related to it, reset the whole file to just a pair of curly braces `{}`.
