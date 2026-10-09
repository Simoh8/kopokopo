# Kopokop Transaction Finder

A secure, local web application designed for Kenya businesses and merchants to search, filter, analyze, and export **Kopokop (Kopo Kopo)** till transaction statements. Built with **Flask** and **Pandas**, all transaction data is processed locally on your machine, ensuring financial privacy and data sovereignty.

---

## Features

- **Local CSV Processing**: Upload Kopokop till CSV statements directly into local memory; no financial data leaves your computer.
- **Smart Column Normalization**: Automatically detects and normalizes standard Kopokop and bank statement headers (`Date`, `Description`, `Account number`, `Reference`, `Debit`, `Credit`, `Balance`).
- **Multi-Criteria Search & Filtering**:
  - Filter by Customer Name (case-insensitive substring match).
  - Search by Transaction Reference number.
  - Filter by Exact Amount or Amount Range (Min / Max).
  - Filter by Date Range (From / To).
  - Keyword and Narrative Search across descriptions.
  - **AND / OR Logic Switch**: Combine filters with strict conjunction (`AND`) or relaxed disjunction (`OR`).
- **Interactive Dashboard & Key Metrics**:
  - Summary cards displaying Total Transactions, Total Credit (Inflow), Total Debit (Outflow), Total Transaction Fees, and Running Balance.
- **Customer Insights & Analytics**:
  - Automatic extraction of customer names from transaction narratives.
  - Aggregated transaction count, total spending, and last active date per customer.
- **Exporting Capabilities**:
  - Export filtered search results directly to **Excel (.xlsx)** with formatted headers.
  - Export filtered search results to standard **CSV (.csv)**.
- **Saved Searches**: Save frequent query combinations for one-click re-execution.
- **Dark-Themed Financial UI**: Responsive, glassmorphism dashboard optimized for financial analysts and business owners.

---

## Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)

---

## Installation Steps

1. **Navigate to the project directory**:
   ```bash
   cd /home/simon/Music/kopokop-finder
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   *(On Windows PowerShell: `.\venv\Scripts\Activate.ps1`)*

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask application**:
   ```bash
   python app.py
   ```

5. **Open in your web browser**:
   Navigate to [http://localhost:5000](http://localhost:5000)

---

## Usage Guide

### 1. Uploading Statements
- Click or drag-and-drop your Kopokop till statement CSV file into the upload zone.
- A sample CSV is available in `sample_data/sample_transactions.csv` to quickly test and explore the dashboard.
- Upon upload, the application parses the data, calculates summary figures, and switches to the transactions view.

### 2. Searching and Filtering
- **Customer Name**: Type a name such as `Karen Wanjiku` or `Arbor Place` to locate all related transactions.
- **Reference**: Look up specific transaction identifiers such as `TXN20240801001`.
- **Amount Filtering**: Enter an exact amount, or specify a minimum and maximum range (e.g., KSh 1,000 to KSh 25,000).
- **Date Range**: Select start and end dates (e.g., `2024-08-01` to `2024-08-31`).
- **Logic Toggle**: Toggle between **AND** (match all criteria) and **OR** (match any criterion).
- Click **Filter Transactions** to apply, or **Reset** to clear active filters.

### 3. Customer Analytics
- Open the **Customers** tab to inspect customer transaction activity.
- View top-paying customers, total volume, transaction counts, and their most recent transaction date.

### 4. Exporting Data
- Once filters are applied, click **Export to CSV** or **Export to Excel** in the action bar.
- The downloaded file contains only the currently filtered dataset.

### 5. Managing Saved Searches
- Save current search parameters with a custom label (e.g., *"Large Corporate Payments"*).
- Re-run saved filters anytime from the sidebar or dropdown menu.

---

## CSV Format Documentation

The application expects standard Kopokop CSV statement files with the following structure:

| Column Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| **`Date`** | Date (YYYY-MM-DD) | Date of transaction | `2024-08-01` |
| **`Description`** | String | Transaction narrative / details | `Payment received from Karen Wanjiku via Till 123456` |
| **`Account number`** | String | Customer phone number or bank account | `0712345678` |
| **`Reference`** | String | Unique transaction ID or M-Pesa receipt | `TXN20240801001` |
| **`Debit`** | Numeric | Amount paid out / fee charged (in KSh) | `35.00` |
| **`Credit`** | Numeric | Amount received (in KSh) | `2700.00` |
| **`Balance`** | Numeric | Running till balance after transaction | `7665.00` |

### Header Flexibility
The parser also supports common variations of these column headers:
- `Transaction Date` &rarr; `Date`
- `Details`, `Narrative`, `Desc` &rarr; `Description`
- `Account No`, `Account` &rarr; `Account number`
- `Ref`, `Reference No` &rarr; `Reference`
- `Amount Debited`, `Paid Out` &rarr; `Debit`
- `Amount Credited`, `Paid In` &rarr; `Credit`
- `Running Balance` &rarr; `Balance`

Monetary values can be plain numbers (e.g., `2700.00`) or include prefixes and formatting (e.g., `KSh 2,700.00`), which are automatically sanitized.

---

## Tech Stack

- **Backend**:
  - Python 3
  - [Flask](https://flask.palletsprojects.com/) (Web framework)
  - [Pandas](https://pandas.pydata.org/) (Data manipulation & in-memory processing)
  - [openpyxl](https://openpyxl.readthedocs.io/) (Excel report generation)
- **Frontend**:
  - Semantic HTML5 & Vanilla CSS3 (Custom Dark Financial Theme)
  - Modern JavaScript (Fetch API, DOM manipulation)
  - [Font Awesome](https://fontawesome.com/) icons & [Inter](https://fonts.google.com/specimen/Inter) font

---

## License

This project is licensed under the [MIT License](LICENSE).
