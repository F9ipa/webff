import os
import requests
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# إعدادات الـ API الخاصة بك
API_URL = "https://www.kaia.sa/ext-api/flightsearch/flights?filter=(EarlyOrDelayedDateTime%20ge%202026-04-19T08:27:49.073%2B03:00%20and%20EarlyOrDelayedDateTime%20lt%202026-04-19T23:59:59.999%2B03:00)%20and%20PublicRemark/Code%20ne%20%27NOP%27%20and%20tolower(FlightNature)%20eq%20%27arrival%27%20and%20Terminal%20eq%20%27T1%27%20and%20(tolower(InternationalStatus)%20eq%20%27international%27)&$orderby=EarlyOrDelayedDateTime&$top=20&$skip=0&$count=true"
AUTH_HEADER = "Basic dGVzdGVyOlRoZVMzY3JldA=="

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    try:
        headers = {
            "Authorization": AUTH_HEADER,
            "Accept": "application/json"
        }
        response = requests.get(API_URL, headers=headers)
        data = response.json()
        
        flights = data.get('value', [])
        
        # تحليل البيانات (الفجوات والذروة)
        analysis = {
            "total_flights": len(flights),
            "total_pax": len(flights) * 200, # افتراضي
            "counter_need": round((len(flights) * 200) / 150),
            "gaps": []
        }

        # حساب الفجوات > 15 دقيقة
        for i in range(1, len(flights)):
            t1 = datetime.fromisoformat(flights[i-1]['EarlyOrDelayedDateTime'].replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(flights[i]['EarlyOrDelayedDateTime'].replace('Z', '+00:00'))
            diff = (t2 - t1).total_seconds() / 60
            
            if diff > 15:
                analysis['gaps'].append({
                    "from": t1.strftime('%H:%M'),
                    "to": t2.strftime('%H:%M'),
                    "duration": int(diff)
                })

        return jsonify({"flights": flights, "analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
