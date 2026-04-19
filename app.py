import os
import json
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# دالة لقراءة البيانات من الملف المحلي
def load_local_data():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading data.json: {e}")
        return {"value": []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    data = load_local_data()
    flights_raw = data.get('value', [])
    
    processed_flights = []
    for f in flights_raw:
        # تنظيف وتحويل الوقت لمعالجته برمجيًا
        raw_time = f['EarlyOrDelayedDateTime'].split('+')[0]
        dt_obj = datetime.strptime(raw_time, '%Y-%m-%dT%H:%M:%S')
        
        processed_flights.append({
            "flight_no": f.get('FullFlightNumber'),
            "airline": f.get('Airline', {}).get('Name'),
            "aircraft": f.get('Aircraft', {}).get('Description'),
            "time_str": dt_obj.strftime('%H:%M'),
            "dt_obj": dt_obj,
            "origin": f.get('RouteOriginAirport', {}).get('City'),
            "remark": f.get('PublicRemark', {}).get('DescriptionAr')
        })

    # فرز الرحلات زمنياً
    processed_flights.sort(key=lambda x: x['dt_obj'])

    # --- تحليل الفجوات والاحتياج ---
    gaps = []
    for i in range(1, len(processed_flights)):
        diff = (processed_flights[i]['dt_obj'] - processed_flights[i-1]['dt_obj']).total_seconds() / 60
        
        # إذا كانت الفجوة بين رحلتين أكثر من 15 دقيقة تُعتبر فجوة تشغيلية
        if diff > 15:
            gaps.append({
                "from": processed_flights[i-1]['time_str'],
                "to": processed_flights[i]['time_str'],
                "duration": int(diff)
            })

    total_flights = len(processed_flights)
    # حساب الركاب: نستخدم سعة المقاعد إذا وجدت، أو متوسط 180
    total_pax = total_flights * 180 
    
    # تحليل الاحتياج (معادلة افتراضية: كاونتر لكل 120 راكب)
    counter_need = round(total_pax / 120) if total_pax > 0 else 0

    analysis = {
        "total_flights": total_flights,
        "total_pax": total_pax,
        "counter_need": counter_need,
        "gaps": gaps,
        "status": "بيانات محلية محدثة"
    }

    # تحويل dt_obj لنص قبل الإرسال لـ JSON
    for f in processed_flights:
        f.pop('dt_obj')

    return jsonify({"flights": processed_flights, "analysis": analysis})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
