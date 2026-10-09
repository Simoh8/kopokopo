import pandas as pd
import io

def export_to_csv(df):
    if df is None or df.empty:
        return ""
    return df.to_csv(index=False)
    
def export_to_excel(df):
    output = io.BytesIO()
    if df is None or df.empty:
        if df is not None:
            df.to_excel(output, index=False)
        output.seek(0)
        return output
        
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')
        workbook = writer.book
        worksheet = writer.sheets['Transactions']
        
        from openpyxl.styles import Font
        header_font = Font(bold=True)
        for cell in worksheet[1]:
            cell.font = header_font
            
        for col_num, column_title in enumerate(df.columns, 1):
            column_letter = worksheet.cell(row=1, column=col_num).column_letter
            
            if column_title in ['Debit', 'Credit', 'Balance', 'amount']:
                for row_num in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row_num, column=col_num)
                    cell.number_format = '#,##0.00'
                    
            max_length = 0
            for cell in worksheet[column_letter]:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
            
    output.seek(0)
    return output
