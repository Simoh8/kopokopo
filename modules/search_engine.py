import pandas as pd
import numpy as np

def search_transactions(df, filters, logic='AND'):
    if df.empty:
        return df
        
    masks = []
    
    if 'customer_name' in filters and filters['customer_name']:
        import re
        cust_str = str(filters['customer_name']).strip()
        names = [n.strip() for n in re.split(r'[,|;]', cust_str) if n.strip()]
        if names:
            m_cust = pd.Series(False, index=df.index)
            for name in names:
                if 'Description' in df.columns:
                    m_cust = m_cust | df['Description'].astype(str).str.contains(name, case=False, na=False)
                if 'Account number' in df.columns:
                    m_cust = m_cust | df['Account number'].astype(str).str.contains(name, case=False, na=False)
            masks.append(m_cust)
        
    if 'exact_amount' in filters and filters['exact_amount'] is not None:
        try:
            amt = float(filters['exact_amount'])
            m = pd.Series(False, index=df.index)
            if 'Debit' in df.columns:
                m = m | (df['Debit'] == amt)
            if 'Credit' in df.columns:
                m = m | (df['Credit'] == amt)
            masks.append(m)
        except ValueError:
            pass
        
    if ('min_amount' in filters and filters['min_amount'] is not None) or ('max_amount' in filters and filters['max_amount'] is not None):
        try:
            min_amt = float(filters.get('min_amount') or 0)
            max_amt = float(filters.get('max_amount') or float('inf'))
            
            m_debit = pd.Series(False, index=df.index)
            m_credit = pd.Series(False, index=df.index)
            
            if 'Debit' in df.columns:
                m_debit = (df['Debit'] >= min_amt) & (df['Debit'] <= max_amt) & (df['Debit'] > 0)
            if 'Credit' in df.columns:
                m_credit = (df['Credit'] >= min_amt) & (df['Credit'] <= max_amt) & (df['Credit'] > 0)
                
            masks.append(m_debit | m_credit)
        except ValueError:
            pass
        
    if 'reference' in filters and filters['reference'] and 'Reference' in df.columns:
        masks.append(df['Reference'].astype(str).str.contains(filters['reference'], case=False, na=False))
        
    if 'description' in filters and filters['description'] and 'Description' in df.columns:
        masks.append(df['Description'].astype(str).str.contains(filters['description'], case=False, na=False))
        
    if 'keyword' in filters and filters['keyword']:
        kw = filters['keyword']
        m = pd.Series(False, index=df.index)
        for col in df.columns:
            if df[col].dtype == object or df[col].dtype == str:
                m = m | df[col].astype(str).str.contains(kw, case=False, na=False)
        masks.append(m)
        
    if ('date_from' in filters and filters['date_from']) or ('date_to' in filters and filters['date_to']):
        if 'Date' in df.columns:
            dates = pd.to_datetime(df['Date'], errors='coerce')
            m = pd.Series(True, index=df.index)
            if 'date_from' in filters and filters['date_from']:
                m = m & (dates >= pd.to_datetime(filters['date_from']))
            if 'date_to' in filters and filters['date_to']:
                m = m & (dates <= pd.to_datetime(filters['date_to']))
            masks.append(m)
            
    if not masks:
        return df
        
    if logic.upper() == 'OR':
        final_mask = masks[0]
        for m in masks[1:]:
            final_mask = final_mask | m
    else: # AND
        final_mask = masks[0]
        for m in masks[1:]:
            final_mask = final_mask & m
            
    return df[final_mask]
