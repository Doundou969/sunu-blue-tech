from flask import Flask, render_template, jsonify, request
import os
import json
from flask_sqlalchemy import SQLAlchemy
from script_peche import job  # Import the job function

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sunu.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class FishingData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    zone = db.Column(db.String(50), nullable=False)
    temp = db.Column(db.Float, nullable=False)
    species = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'zone': self.zone,
            'temp': self.temp,
            'species': self.species
        }

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
    data = FishingData.query.all()
    return jsonify([item.to_dict() for item in data])

@app.route('/api/run-script', methods=['POST'])
def run_script():
    try:
        job()
        # Load generated data and save to DB
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Clear existing data
            db.session.query(FishingData).delete()
            # Add new data
            for item in data:
                db_data = FishingData(
                    date=item['date'],
                    zone=item['zone'],
                    temp=item['temp'],
                    species=item['species']
                )
                db.session.add(db_data)
            db.session.commit()
        except FileNotFoundError:
            pass
        return jsonify({"status": "success", "message": "Script exécuté et données sauvegardées en DB"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add default data if empty
        if FishingData.query.count() == 0:
            default_data = [
                {"date": "2026-01-22", "zone": "Dakar", "temp": 24.5, "species": "Sardine, Thon"},
                {"date": "2026-01-21", "zone": "Cap Vert", "temp": 23.8, "species": "Maquereau"},
                {"date": "2026-01-20", "zone": "Goree", "temp": 25.2, "species": "Poisson volant"}
            ]
            for item in default_data:
                db_data = FishingData(
                    date=item['date'],
                    zone=item['zone'],
                    temp=item['temp'],
                    species=item['species']
                )
                db.session.add(db_data)
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)