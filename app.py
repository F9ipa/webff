import os
import requests
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

AUTH_HEADER = "Basic dGVzdGVyOlRoZVMzY3JldA=="

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    # استقبال الوقت من المتصفح أو استخدام الافتراضي
    start_time = request.args.get('start')
    end_time = request.args.get('end')
    
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # إذا لم يحدد المستخدم وقت، نأخذ من الآن وحتى نهاية اليوم
    if not start_time:
        start_time = datetime.now().strftime('%H:%M')
    if not end_time:
        end_time = "23:59"

    # بناء تواريخ الـ API بشكل صحيح
    formatted_start = f"{today_date}T{start_time}:00.000+03:00"
    formatted_end = f"{today_date}T{end_time}:59.999+03:00"

    url = (
        f"https://www.kaia.sa/ext-api/flightsearch/flights?"
        f"filter=(EarlyOrDelayedDateTime ge {formatted_start} and EarlyOrDelayedDateTime lt {formatted_end}) "
        f"and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' "
        f"and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international') "
        f"&$orderby=EarlyOrDelayedDateTime&$top=100&$count=true"
    )

    try:
        response = requests.get(url, headers={"Authorization": AUTH_HEADER, "Accept": "application/json"})
        data = response.json()
        flights = data.get('value', [])
        
        # تحليل البيانات (الفجوات والركاب)
        analysis = {"gaps": [], "total_pax": len(flights) * 200, "counter_need": round((len(flights) * 200) / 150)}
        
        for i in range(1, len(flights)):
            t1 = datetime.fromisoformat(flights[i-1]['EarlyOrDelayedDateTime'].replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(flights[i]['EarlyOrDelayedDateTime'].replace('Z', '+00:00'))
            diff = (t2 - t1).total_seconds() / 60
            if diff > 15:
                analysis['gaps'].append({"from": t1.strftime('%H:%M'), "to": t2.strftime('%H:%M'), "duration": int(diff)})

        return jsonify({"flights": flights, "analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
