from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import json
import io
import get_ogimet_data
import convert_to_geojson

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        start_str = request.form['start_time']
        end_str = request.form['end_time']
        
        # HTML datetime-local format: YYYY-MM-DDTHH:MM
        start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
        end_dt = datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
        
        # Fetch data
        print(f"Fetching data for {start_dt} to {end_dt}...")
        raw_text = get_ogimet_data.get_data_for_range(start_dt, end_dt)
        
        # Convert to GeoJSON
        print("Converting to GeoJSON...")
        stations = convert_to_geojson.parse_stations_from_text(raw_text)
        
        geojson = {
            "type": "FeatureCollection",
            "features": stations
        }
        
        # Create a file-like object to send
        mem = io.BytesIO()
        mem.write(json.dumps(geojson, indent=2).encode('utf-8'))
        mem.seek(0)
        
        filename = f"weather_stations_{start_dt.strftime('%Y%m%d%H%M')}_{end_dt.strftime('%Y%m%d%H%M')}.geojson"
        
        return send_file(
            mem,
            as_attachment=True,
            download_name=filename,
            mimetype='application/geo+json'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)
