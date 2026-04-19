import os
import requests
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# بيانات الاعتماد والروابط
AUTH_HEADER = "Basic dGVzdGVyOlRoZVMzY3JldA=="

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    # 1. جلب الوقت من المتصفح
    start_t = request.args.get('start', '00:00')
    end_t = request.args.get('end', '23:59')
    today = datetime.now().strftime('%Y-%m-%d')

    # 2. بناء الفلتر الزمني بدقة (تنسيق ISO مع الترميز)
    start_val = f"{today}T{start_t}:00.000+03:00"
    end_val = f"{today}T{end_t}:59.999+03:00"

    # 3. بناء الرابط مع الالتزام بصيغة OData
    filter_query = (
        f"(EarlyOrDelayedDateTime ge {start_val} and EarlyOrDelayedDateTime lt {end_val}) "
        f"and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' "
        f"and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')"
    )
    
    # تحويل الفلتر لصيغة تفهمها الروابط (URL Encoding)
    encoded_filter = urllib.parse.quote(filter_query)
    
    final_url = f"https://www.kaia.sa/ext-api/flightsearch/flights?filter={encoded_filter}&$orderby=EarlyOrDelayedDateTime&$top=100&$count=true"

    headers = {
        "Authorization": AUTH_HEADER,
        "Accept": "application/json",
        "OData-Version": "4.0",
        "Prefer": "odata.maxpagesize=20",
        "User-Agent": "Mozilla/5.0" # لإيهام السيرفر أن الطلب من متصفح
    }

    try:
        # طلب البيانات مع مهلة زمنية 15 ثانية
        response = requests.get(final_url, headers=headers, timeout=15)
        
        # التحقق من حالة الرد
        if response.status_code != 200:
            return jsonify({"error": f"API Error: {response.status_code}", "details": response.text}), response.status_code
            
        data = response.json()
        flights = data.get('value', [])
        
        # تحليل البيانات (الفجوات والركاب)
        analysis = process_data(flights)
        
        return jsonify({"flights": flights, "analysis": analysis})

    except Exception as e:
        return jsonify({"error": "Server Connection Failed", "details": str(e)}), 500

def process_data(flights):
    gaps = []
    for i in range(1, len(flights)):
        try:
            t1 = datetime.fromisoformat(flights[i-1]['EarlyOrDelayedDateTime'].replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(flights[i]['EarlyOrDelayedDateTime'].replace('Z', '+00:00'))
            diff = (t2 - t1).total_seconds() / 60
            if diff > 15:
                gaps.append({"from": t1.strftime('%H:%M'), "to": t2.strftime('%H:%M'), "duration": int(diff)})
        except: continue
            
    pax = len(flights) * 180
    return {"total_pax": pax, "counter_need": round(pax / 120), "gaps": gaps}

if __name__ == '__main__':
    # مهم جداً لعمل Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
