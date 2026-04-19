import os
import json
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

def get_local_json():
    # تأكد أن ملف data.json موجود في نفس المجلد
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"value": []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    raw_data = get_local_json()
    flights_list = raw_data.get('value', [])
    
    processed = []
    for f in flights_list:
        try:
            # معالجة الوقت
            dt_str = f.get('EarlyOrDelayedDateTime', '').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_str)
            
            processed.append({
                "time_str": dt_obj.strftime('%H:%M'),
                "airline": f.get('Airline', {}).get('Name', 'N/A'),
                "flight_no": f.get('FullFlightNumber', 'N/A'),
                "origin": f.get('RouteOriginAirport', {}).get('City', 'غير معروف'),
                "dt": dt_obj
            })
        except:
            continue

    # ترتيب حسب الوقت
    processed.sort(key=lambda x: x['dt'])
    
    # حذف كائن الـ datetime قبل الإرسال
    for item in processed:
        item.pop('dt')

    return jsonify({"flights": processed})

if __name__ == '__main__':
    app.run(debug=True)
