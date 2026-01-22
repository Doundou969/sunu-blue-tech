from flask import Flask, render_template, jsonify, request
import os
import json
from script_peche import job  # Import the job function

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/api/data')
def get_data():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify([])

@app.route('/api/run-script', methods=['POST'])
def run_script():
    try:
        job()
        return jsonify({"status": "success", "message": "Script exécuté avec succès"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Create templates directory and move HTML files
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Copy HTML files to templates
    import shutil
    for file in ['index.html', 'about.html', 'services.html']:
        if os.path.exists(file):
            shutil.copy(file, f'templates/{file}')
    
    app.run(debug=True, host='0.0.0.0', port=5000)