# Recreation Permit Notifs

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

#### 1.2.2 Chrome
Make sure you have [Google Chrome](https://www.google.com/chrome/) installed as this app uses Selenium's Chrome web driver to access [recreation.gov](https://recreation.gov).

## 2. Running
### 2.1 Settings
Settings are defined in [settings.json](settings.json). 
TODO format
```JSON
{
    "show-browser":true,
    "emails": {
        "sendFrom": {
            "email": "send-from@example.com",
            "pass": "email password"
        },
        "sendTo": ["send-to@example.com"]
    },
    "dates": {
        "start": "March 2022",
        "end": "September 2022"
    },
    "run-every": 10,
    "run-once": true,
    "wait-for-load": 2,
    "permits": [{
        "id": 12345,
        "segments": ["Segment 1"],
        "num-people": 5
    }]
}
```

### 2.2 Running The Code
Simply run `main.py` with `pipenv`:

```bash
pipenv run python main.py
```

Running this with `pipenv` will ensure that dependencies are installed and will set up a virtual environment for the code to run in. To close the program, close your shell or input `CTRL+c`.