# Panel Manufacturing Calculator

This project provides a set of tools to calculate material requirements, costs, and manufacturing times for panel production. It can be used as a command-line tool or through a web-based interface.

## Features

-   **Detailed Bill of Materials:** Generates a detailed list of all the parts and their dimensions.
-   **Raw Material Calculation:** Calculates the required raw materials (profiles) and optimizes their use.
-   **Welding and Time Estimation:** Estimates the necessary welding and the time required for each panel.
-   **Cost Analysis:** Provides a detailed cost analysis per panel, including material, labor, and overhead costs.
-   **Multiple Reports:** Can generate various reports, such as detailed cutting lists, material summaries, and cost breakdowns.

## How to Use

### Command-Line Interface

The CLI tool `script.py` processes a `paneles.csv` file to generate different reports.

**Prerequisites:**

-   Python 3.x

**Usage:**

1.  **Prepare the input file:** Get `paneles.csv` file ready
1. **Prepare environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2.  **Run the script:**
    ```bash
    python3 script.py
    ```
3.  **Follow the prompts:** The script will ask for the current USD to CLP exchange rate and then present a menu of available reports.

### Web Interface

The web interface provides a user-friendly way to perform the same calculations.

**Prerequisites:**

-   Python 3.x
-   Streamlit and Pandas libraries (`pip install streamlit pandas`)

**Usage:**

1. **Prepare environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
1.  **Run the Streamlit app:**
    ```bash
    streamlit run web.py
    ```
2.  **Upload the `paneles.csv` file:** Use the file uploader in the web interface.
3.  **Select a report:** Choose the desired report from the radio buttons.

## Testing

The `backend.py` file includes a set of inline tests to verify the correctness of the calculations. To run the tests, execute the `backend.py` script directly:

```bash
python backend.py
```

If all tests pass, there will be no output. If a test fails, an `AssertionError` will be raised with details about the failure.

## Environment

This was tested on a MacBook Air with an M3 chip using Python 3.9.6.


## TODO

- [ ] Read from uploaded csv file
- [ ] Download data to file
