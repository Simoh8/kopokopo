import pandas as pd
import numpy as np
import io
import re

def clean_money(val):
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str:
        return 0.0
    # Accounting negative format (100.00) -> -100.00
    is_neg = False
    if val_str.startswith('(') and val_str.endswith(')'):
        is_neg = True
        val_str = val_str[1:-1]
    elif val_str.startswith('-'):
        is_neg = True
        val_str = val_str[1:]

    val_str = val_str.replace(',', '').replace(' ', '')
    val_str = re.sub(r'(?i)ksh|kes|\$', '', val_str)
    try:
        res = float(val_str)
        return -res if is_neg else res
    except Exception:
        return 0.0

def parse_csv(filepath_or_buffer, filename=''):
    encodings = ['utf-8-sig', 'utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252', 'iso-8859-1']
    df = None
    read_error = None
    
    # Ensure file pointer at start if file object
    if isinstance(filepath_or_buffer, str):
        filename = filename or filepath_or_buffer
        with open(filepath_or_buffer, 'rb') as f:
            raw_bytes = f.read()
    else:
        try:
            filepath_or_buffer.seek(0)
        except Exception:
            pass
        raw_bytes = filepath_or_buffer.read()
        
    if not raw_bytes:
        return {'success': False, 'errors': ['The uploaded file is empty (0 bytes). Please select a valid transaction file.']}

    fn_lower = filename.lower()

    # 0. Check for PDF file
    if raw_bytes.startswith(b'%PDF-'):
        return {
            'success': False,
            'errors': ['PDF files are not supported directly. Please export/download your statement as a CSV or Excel (.xlsx) file from your Kopokop dashboard.']
        }

    # 1. Try Excel read if filename suggests excel or bytes look binary
    if fn_lower.endswith(('.xlsx', '.xls')) or raw_bytes.startswith(b'PK') or raw_bytes.startswith(b'\xd0\xcf\x11\xe0'):
        try:
            sheets = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
            if isinstance(sheets, dict):
                # Pick first non-empty sheet
                for s_name, s_df in sheets.items():
                    if not s_df.empty:
                        df = s_df
                        break
            elif isinstance(sheets, pd.DataFrame):
                df = sheets
        except Exception as e:
            read_error = f"Excel parse error: {str(e)}"

    # 2. Try ZIP archive extraction if PK zip header
    if df is None and raw_bytes.startswith(b'PK'):
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                for zname in zf.namelist():
                    if zname.lower().endswith(('.csv', '.xlsx', '.xls', '.tsv', '.txt')):
                        with zf.open(zname) as zitem:
                            return parse_csv(zitem, filename=zname)
        except Exception as e:
            read_error = f"ZIP extract error: {str(e)}"

    # 3. Try HTML table read if file contains html tags
    if df is None and (b'<table' in raw_bytes.lower() or b'<html' in raw_bytes.lower()):
        try:
            dfs = pd.read_html(io.BytesIO(raw_bytes))
            if dfs:
                for temp_df in dfs:
                    if not temp_df.empty:
                        df = temp_df
                        break
        except Exception as e:
            read_error = f"HTML table parse error: {str(e)}"

    # 4. Try CSV / TSV read with pandas using various encodings and delimiters
    if df is None:
        header_keywords = ['date', 'time', 'desc', 'details', 'narrative', 'ref', 'debit', 'credit', 'amount', 'balance', 'account', 'phone', 'paid']

        for enc in encodings:
            try:
                content_str = raw_bytes.decode(enc)
                content_str = content_str.replace('\x00', '')
                lines = content_str.splitlines()

                # Pre-scan lines for table header row to handle Kopokop metadata header blocks
                skiprows_idx = 0
                for i, line in enumerate(lines[:100]):
                    line_lower = line.lower()
                    matches = sum(1 for kw in header_keywords if kw in line_lower)
                    if matches >= 2:
                        skiprows_idx = i
                        break

                skip_options = [skiprows_idx]
                if skiprows_idx != 0:
                    skip_options.append(0)

                for skip in skip_options:
                    for sep in [None, ',', ';', '\t', '|']:
                        try:
                            buf = io.StringIO(content_str)
                            if sep is None:
                                temp_df = pd.read_csv(buf, skiprows=skip, sep=None, engine='python', on_bad_lines='skip')
                            else:
                                temp_df = pd.read_csv(buf, skiprows=skip, sep=sep, on_bad_lines='skip')
                                
                            if len(temp_df.columns) > 1 or sep == ',':
                                df = temp_df
                                break
                        except Exception:
                            continue
                    if df is not None:
                        break
                if df is not None:
                    break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                read_error = str(e)
            
    if df is None:
        sample_hex = raw_bytes[:50].hex()
        return {
            'success': False,
            'errors': [f"Failed to decode or parse transaction file '{filename}'. Error details: {read_error or 'Unrecognized format'}. (Header bytes: {sample_hex})"]
        }

    # If first row(s) look like metadata/title and headers are further down, search for header row
    def is_header_row(columns):
        col_str = " ".join([str(c).lower() for c in columns])
        keywords = ['date', 'time', 'desc', 'details', 'narrative', 'ref', 'debit', 'credit', 'amount', 'balance', 'account', 'phone', 'paid']
        return sum(1 for kw in keywords if kw in col_str) >= 2

    if not is_header_row(df.columns) and len(df) > 0:
        # Check first 50 rows to see if any row looks like a header
        for skiprows in range(1, min(50, len(df))):
            try:
                if 'content_str' in locals():
                    buf = io.StringIO(content_str)
                    temp_df = pd.read_csv(buf, skiprows=skiprows, on_bad_lines='skip')
                    if is_header_row(temp_df.columns):
                        df = temp_df
                        break
            except Exception:
                continue

    # Strip whitespace, BOM, quotes from column names
    df.columns = [re.sub(r'[\ufeff"\']', '', str(c)).strip() for c in df.columns]

    # Exhaustive Column Mapping
    col_map = {}
    found_types = set()

    for col in df.columns:
        c_clean = str(col).lower().strip()
        c_clean_alphanumeric = re.sub(r'[^a-z0-9]', '', c_clean)

        # Date aliases
        if any(kw in c_clean for kw in ['date', 'time', 'timestamp', 'created', 'posted', 'completed', 'period']) or c_clean_alphanumeric in ['date', 'time', 'createdat']:
            if 'Date' not in found_types:
                col_map[col] = 'Date'
                found_types.add('Date')

        # Description aliases
        elif any(kw in c_clean for kw in ['desc', 'detail', 'narrat', 'remark', 'comment', 'subject', 'particular', 'type', 'channel', 'note', 'reason', 'summary', 'product', 'service', 'item']) or c_clean_alphanumeric in ['desc', 'description', 'details']:
            if 'Description' not in found_types:
                col_map[col] = 'Description'
                found_types.add('Description')

        # Account number / Customer aliases
        elif any(kw in c_clean for kw in ['account', 'phone', 'mobile', 'msisdn', 'customer', 'client', 'payer', 'payee', 'sender', 'recipient', 'counterparty', 'name', 'number']):
            if 'Account number' not in found_types:
                col_map[col] = 'Account number'
                found_types.add('Account number')

        # Reference aliases
        elif any(kw in c_clean for kw in ['ref', 'receipt', 'voucher', 'id', 'code', 'txn', 'transactionid', 'reference']):
            if 'Reference' not in found_types:
                col_map[col] = 'Reference'
                found_types.add('Reference')

        # Debit aliases
        elif any(kw in c_clean for kw in ['debit', 'paidout', 'moneyout', 'withdrawal', 'spent', 'dr', 'disbursement', 'charge', 'fee', 'out']) or c_clean_alphanumeric in ['debit', 'paidout', 'out']:
            if 'Debit' not in found_types:
                col_map[col] = 'Debit'
                found_types.add('Debit')

        # Credit aliases
        elif any(kw in c_clean for kw in ['credit', 'paidin', 'moneyin', 'deposit', 'received', 'cr', 'receipt', 'inflow', 'in']) or c_clean_alphanumeric in ['credit', 'paidin', 'in']:
            if 'Credit' not in found_types:
                col_map[col] = 'Credit'
                found_types.add('Credit')

        # Single Amount alias
        elif any(kw in c_clean for kw in ['amount', 'val', 'sum', 'total', 'net', 'kes', 'ksh', 'value']) or c_clean_alphanumeric in ['amount', 'value']:
            if 'Amount' not in found_types:
                col_map[col] = 'Amount'
                found_types.add('Amount')

        # Balance aliases
        elif any(kw in c_clean for kw in ['bal', 'balance', 'running', 'closing']) or c_clean_alphanumeric in ['balance', 'runningbalance', 'bal']:
            if 'Balance' not in found_types:
                col_map[col] = 'Balance'
                found_types.add('Balance')

    df = df.rename(columns=col_map)

    # Positional Fallback if NO columns matched keyword rules
    recognized = [c for c in ['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance', 'Account number', 'Amount'] if c in df.columns]
    if len(recognized) == 0 and len(df.columns) >= 2:
        # Infer column types by inspecting data in first few rows
        for idx, col in enumerate(df.columns):
            sample_vals = df[col].dropna().astype(str).tolist()[:5]
            sample_str = " ".join(sample_vals)
            
            # Check if dates
            if 'Date' not in df.columns and any(re.search(r'\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2}', v) for v in sample_vals):
                df = df.rename(columns={col: 'Date'})
            # Check if money numbers
            elif any(kw not in df.columns for kw in ['Credit', 'Debit', 'Amount']):
                numeric_count = sum(1 for v in sample_vals if re.match(r'^-?\(?\d+(?:,\d+)*(?:\.\d+)?\)?$', v.strip().replace('KSh','').replace('KES','').replace(' ','')))
                if numeric_count >= 3:
                    if 'Credit' not in df.columns:
                        df = df.rename(columns={col: 'Credit'})
                    elif 'Debit' not in df.columns:
                        df = df.rename(columns={col: 'Debit'})
            # Check if short alphanumeric code (Reference)
            elif 'Reference' not in df.columns and any(re.match(r'^[A-Z0-9]{6,20}$', v.strip()) for v in sample_vals):
                df = df.rename(columns={col: 'Reference'})
            # Fallback to Description
            elif 'Description' not in df.columns:
                df = df.rename(columns={col: 'Description'})

    # If single Amount column was found and no Debit/Credit:
    if 'Amount' in df.columns and 'Debit' not in df.columns and 'Credit' not in df.columns:
        def split_amount_debit(row):
            amt = row['Amount']
            if isinstance(amt, (int, float)):
                return abs(amt) if amt < 0 else 0.0
            s_amt = str(amt).strip()
            if s_amt.startswith('-') or s_amt.startswith('('):
                return abs(clean_money(s_amt))
            return 0.0

        def split_amount_credit(row):
            amt = row['Amount']
            if isinstance(amt, (int, float)):
                return amt if amt > 0 else 0.0
            s_amt = str(amt).strip()
            if not s_amt.startswith('-') and not s_amt.startswith('('):
                return clean_money(s_amt)
            return 0.0

        df['Debit'] = df.apply(split_amount_debit, axis=1)
        df['Credit'] = df.apply(split_amount_credit, axis=1)

    # Fill missing essential columns with smart defaults
    if 'Debit' not in df.columns:
        df['Debit'] = 0.0
    if 'Credit' not in df.columns:
        df['Credit'] = 0.0
    if 'Account number' not in df.columns:
        df['Account number'] = ''
    if 'Reference' not in df.columns:
        df['Reference'] = [f"REF-{i+1}" for i in range(len(df))]
    if 'Description' not in df.columns:
        df['Description'] = 'Transaction'

    money_cols = ['Debit', 'Credit', 'Balance']
    for mc in money_cols:
        if mc in df.columns:
            df[mc] = df[mc].apply(clean_money)

    # Auto-calculate missing Balance column if not provided
    if 'Balance' not in df.columns or df['Balance'].sum() == 0:
        running_bal = 0.0
        balances = []
        for _, row in df.iterrows():
            credit = row.get('Credit', 0.0)
            debit = row.get('Debit', 0.0)
            running_bal += (credit - debit)
            balances.append(round(running_bal, 2))
        df['Balance'] = balances

    # Date parsing
    if 'Date' in df.columns:
        parsed_dates = pd.to_datetime(df['Date'], errors='coerce')
        df['Date'] = parsed_dates.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else '')
    else:
        df['Date'] = ''

    # Clean up NaN / Nulls
    for c in df.columns:
        if df[c].dtype in ['float64', 'int64', 'float32', 'int32']:
            df[c] = df[c].fillna(0)
        else:
            df[c] = df[c].fillna('')

    return {
        'success': True,
        'data': df.to_dict(orient='records'),
        'columns': list(df.columns),
        'errors': [],
        'row_count': len(df)
    }
