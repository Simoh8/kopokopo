import os
import json
import uuid
import pandas as pd
from flask import Flask, request, jsonify, render_template, session, send_file, Response
try:
    from flask_cors import CORS
except ImportError:
    def CORS(app):
        pass
from config import Config
from modules.csv_parser import parse_csv
from modules.search_engine import search_transactions
from modules.analytics import get_dashboard_stats, get_customer_analysis
from modules.exporter import export_to_csv, export_to_excel

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
SAVED_SEARCHES_FILE = os.path.join(app.config['UPLOAD_FOLDER'], 'saved_searches.json')

# In-memory store for dataframes. In production, use a database or redis.
SESSION_STORE = {}

def get_dataframe(session_id):
    return SESSION_STORE.get(session_id)

def set_dataframe(session_id, df):
    SESSION_STORE[session_id] = df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded in request'}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    allowed = ('.csv', '.xlsx', '.xls', '.tsv', '.txt')
    if file and (file.filename.lower().endswith(allowed) or '.' not in file.filename):
        try:
            result = parse_csv(file, filename=file.filename)
            if not result.get('success'):
                err_msg = result.get('errors', ['Failed to parse file'])[0]
                print(f"[UPLOAD ERROR] {file.filename}: {err_msg}")
                return jsonify({'error': err_msg, 'details': result.get('errors')}), 400
                
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            
            df = pd.DataFrame(result['data'])
            set_dataframe(session_id, df)
            
            stats = get_dashboard_stats(df)
            
            return jsonify({
                'success': True,
                'message': 'File uploaded and parsed successfully',
                'session_id': session_id,
                'row_count': result['row_count'],
                'columns': result['columns'],
                'stats': stats
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to process file: {str(e)}'}), 400
        
    return jsonify({'error': 'Invalid file type. Supported formats: CSV, Excel (.xlsx, .xls), TSV, TXT.'}), 400

@app.route('/api/search', methods=['POST'])
def search():
    session_id = request.headers.get('X-Session-Id') or session.get('session_id')
    df = get_dataframe(session_id)
    if df is None:
        return jsonify({'error': 'No data found. Please upload a file first.'}), 404
        
    data = request.json or {}
    filters = data.get('filters', {})
    logic = data.get('logic', 'AND')
    page = int(data.get('page', 1))
    per_page = int(data.get('per_page', 50))
    
    filtered_df = search_transactions(df, filters, logic)
    
    total = len(filtered_df)
    pages = (total + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered_df.iloc[start:end]
    
    result_data = paginated.to_dict(orient='records')
    for row in result_data:
        for k, v in row.items():
            if isinstance(v, float) and not pd.isna(v):
                row[k] = round(v, 2)
                
    return jsonify({
        'results': result_data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages
    })

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/stats', methods=['GET'])
def stats():
    session_id = request.headers.get('X-Session-Id') or session.get('session_id')
    df = get_dataframe(session_id)
    if df is None:
        return jsonify({
            'loaded': False,
            'total_transactions': 0,
            'total_received': 0,
            'total_paid_out': 0,
            'total_fees': 0,
            'net_balance': 0
        }), 200
        
    stats_data = get_dashboard_stats(df)
    stats_data['loaded'] = True
    for k, v in stats_data.items():
        if isinstance(v, float) and not pd.isna(v):
            stats_data[k] = round(v, 2)
            
    return jsonify(stats_data)

@app.route('/api/customers', methods=['GET'])
def customers():
    session_id = request.headers.get('X-Session-Id') or session.get('session_id')
    df = get_dataframe(session_id)
    if df is None:
        return jsonify({'error': 'No data found. Please upload a file first.'}), 404
        
    analysis = get_customer_analysis(df)
    for row in analysis:
        if 'total_amount' in row and isinstance(row['total_amount'], float):
            row['total_amount'] = round(row['total_amount'], 2)
            
    return jsonify({'customers': analysis})

@app.route('/api/export/csv', methods=['GET'])
def export_csv_route():
    session_id = request.headers.get('X-Session-Id') or session.get('session_id')
    df = get_dataframe(session_id)
    if df is None:
        return jsonify({'error': 'No data found. Please upload a file first.'}), 404
        
    filters = request.args.to_dict()
    logic = filters.pop('logic', 'AND')
    filtered_df = search_transactions(df, filters, logic)
    
    csv_data = export_to_csv(filtered_df)
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=export.csv"}
    )

@app.route('/api/export/excel', methods=['GET'])
def export_excel_route():
    session_id = request.headers.get('X-Session-Id') or session.get('session_id')
    df = get_dataframe(session_id)
    if df is None:
        return jsonify({'error': 'No data found. Please upload a file first.'}), 404
        
    filters = request.args.to_dict()
    logic = filters.pop('logic', 'AND')
    filtered_df = search_transactions(df, filters, logic)
    
    excel_io = export_to_excel(filtered_df)
    
    return send_file(
        excel_io,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='export.xlsx'
    )

@app.route('/api/saved-searches', methods=['GET', 'POST'])
def handle_saved_searches():
    if not os.path.exists(SAVED_SEARCHES_FILE):
        with open(SAVED_SEARCHES_FILE, 'w') as f:
            json.dump([], f)
            
    if request.method == 'GET':
        with open(SAVED_SEARCHES_FILE, 'r') as f:
            searches = json.load(f)
        return jsonify({'searches': searches})
        
    if request.method == 'POST':
        data = request.json or {}
        new_search = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', 'Untitled Search'),
            'filters': data.get('filters', {}),
            'logic': data.get('logic', 'AND')
        }
        
        with open(SAVED_SEARCHES_FILE, 'r') as f:
            searches = json.load(f)
            
        searches.append(new_search)
        
        with open(SAVED_SEARCHES_FILE, 'w') as f:
            json.dump(searches, f)
            
        return jsonify({'success': True, **new_search}), 201

@app.route('/api/saved-searches/<search_id>', methods=['DELETE'])
def delete_saved_search(search_id):
    if not os.path.exists(SAVED_SEARCHES_FILE):
        return jsonify({'error': 'Not found'}), 404
        
    with open(SAVED_SEARCHES_FILE, 'r') as f:
        searches = json.load(f)
        
    initial_len = len(searches)
    searches = [s for s in searches if s.get('id') != search_id]
    
    if len(searches) == initial_len:
        return jsonify({'error': 'Not found'}), 404
        
    with open(SAVED_SEARCHES_FILE, 'w') as f:
        json.dump(searches, f)
        
    return jsonify({'message': 'Deleted successfully'}), 200

@app.route('/api/transaction/<int:index>', methods=['GET'])
def get_transaction(index):
    session_id = request.headers.get('X-Session-Id') or session.get('session_id')
    df = get_dataframe(session_id)
    if df is None:
        return jsonify({'error': 'No data found. Please upload a file first.'}), 404
        
    if index < 0 or index >= len(df):
        return jsonify({'error': 'Transaction not found.'}), 404
        
    tx = df.iloc[index].to_dict()
    for k, v in tx.items():
        if isinstance(v, float) and not pd.isna(v):
            tx[k] = round(v, 2)
            
    return jsonify(tx)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
