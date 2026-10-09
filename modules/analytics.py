import pandas as pd
import re

def get_dashboard_stats(df):
    stats = {
        'total_transactions': 0,
        'total_credit': 0.0,
        'total_debit': 0.0,
        'total_fees': 0.0,
        'net_balance': 0.0
    }
    if df is None or df.empty:
        return stats
        
    stats['total_transactions'] = len(df)
    
    if 'Credit' in df.columns:
        stats['total_credit'] = float(df['Credit'].sum())
    if 'Debit' in df.columns:
        stats['total_debit'] = float(df['Debit'].sum())
        
    if 'Description' in df.columns and 'Debit' in df.columns:
        fees_df = df[df['Description'].astype(str).str.contains('fee|charge', case=False, na=False)]
        stats['total_fees'] = float(fees_df['Debit'].sum())
        
    if 'Balance' in df.columns and not df['Balance'].empty:
        stats['net_balance'] = float(df['Balance'].iloc[-1])
    else:
        stats['net_balance'] = stats['total_credit'] - stats['total_debit']
        
    return stats

def get_customer_analysis(df):
    if df is None or df.empty or 'Description' not in df.columns:
        return []
        
    def extract_customer(desc):
        if not isinstance(desc, str):
            return "Unknown"
        
        # Try to extract name from common patterns
        patterns = [
            r'(?i)(?:payment\s+)?(?:received\s+)?from\s+(.+?)(?:\s+via\b.*)?$',
            r'(?i)by\s+(.+?)(?:\s+via\b.*)?$',
            r'(?i)to\s+(.+?)(?:\s+via\b.*)?$',
        ]
        for p in patterns:
            match = re.search(p, desc)
            if match:
                name = match.group(1).strip()
                # Remove trailing 'via Till...' if still present
                name = re.sub(r'\s+via\s+.*$', '', name, flags=re.IGNORECASE).strip()
                if name:
                    return name
        return desc.strip()
        
    temp_df = df.copy()
    temp_df['customer_name'] = temp_df['Description'].apply(extract_customer)
    
    temp_df['amount'] = 0.0
    if 'Credit' in temp_df.columns:
        temp_df['amount'] += temp_df['Credit'].fillna(0)
    if 'Debit' in temp_df.columns:
        temp_df['amount'] += temp_df['Debit'].fillna(0)
        
    if 'Date' in temp_df.columns:
        temp_df['Date_obj'] = pd.to_datetime(temp_df['Date'], errors='coerce')
    else:
        temp_df['Date_obj'] = pd.NaT
        
    grouped = temp_df.groupby('customer_name').agg(
        transaction_count=('Description', 'count'),
        total_amount=('amount', 'sum'),
        last_transaction_date=('Date_obj', 'max')
    ).reset_index()
    
    grouped['last_transaction_date'] = grouped['last_transaction_date'].apply(
        lambda x: x.isoformat() if pd.notnull(x) else None
    )
    
    grouped = grouped.sort_values('total_amount', ascending=False)
    return grouped.to_dict(orient='records')
