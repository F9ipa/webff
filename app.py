import os
import json
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from collections import Counter

app = Flask(__name__)

def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f).get('value', [])
    return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    all_flights = load_data()
    now = datetime.now()
    
    processed_flights = []
    flight_times = []
    delayed_count = 0
    hourly_stats = Counter()

    for f in all_flights:
        status = f.get('PublicRemark', {})
        status_code = status.get('Code', '').upper()
        
        # تنفيذ شرطك: استبعاد الرحلات التي وصلت أو هبطت
        if status_code in ['ARR', 'DLV', 'LND']:
            continue

        dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
        dt_obj = datetime.fromisoformat(dt_raw)
        
        flight_info = {
            "time": dt_obj.strftime('%H:%M'),
            "airline": f.get('Airline', {}).get('Name'),
            "flight_no": f.get('FullFlightNumber'),
            "origin": f.get('RouteOriginAirport', {}).get('City'),
            "status_ar": status.get('DescriptionAr'),
            "status_code": status_code
        }
        
        processed_flights.append(flight_info)
        flight_times.append(dt_obj)
        hourly_stats[dt_obj.hour] += 1
        if status_code == 'DEL': delayed_count += 1

    # حساب الفجوات (نفس منطق كودك)
    gaps = []
    flight_times.sort()
    for i in range(len(flight_times) - 1):
        diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
        if diff > 15:
            gaps.append({
                "from": flight_times[i].strftime('%H:%M'),
                "to": flight_times[i+1].strftime('%H:%M'),
                "duration": int(diff)
            })

    # تحديد وقت الذروة
    peak_hour = "لا يوجد"
    peak_count = 0
    if hourly_stats:
        hour = max(hourly_stats, key=hourly_stats.get)
        peak_hour = f"{hour:02d}:00"
        peak_count = hourly_stats[hour]

    return jsonify({
        "flights": processed_flights,
        "analysis": {
            "total_pending": len(processed_flights),
            "delayed": delayed_count,
            "peak_time": peak_hour,
            "peak_count": peak_count,
            "gaps": gaps,
            "counter_need": round(len(processed_flights) * 180 / 120) # معادلة الاحتياج
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
