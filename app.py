from flask import Flask, render_template, request
import requests
from datetime import datetime
from collections import Counter
import math

app = Flask(__name__)

class FlightAnalyzer:
    def __init__(self):
        self.url = "https://www.kaia.sa/ext-api/flightsearch/flights"
        self.headers = {
            "Accept": "application/json",
            "Authorization": "Basic dGVzdGVyOlRoZVMzY3JldA==",
            "User-Agent": "Mozilla/5.0"
        }

    def fetch_data(self, start_dt, end_dt):
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {start_dt} and EarlyOrDelayedDateTime lt {end_dt}) and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')",
            "$orderby": "EarlyOrDelayedDateTime",
            "$count": "true"
        }
        try:
            response = requests.get(self.url, params=params, headers=self.headers, timeout=10)
            return response.json().get('value', [])
        except: return []

def format_time_12h(dt_obj):
    # تنسيق الوقت لنظام 12 ساعة (ص/م)
    hour = dt_obj.hour
    period = "ص" if hour < 12 else "م"
    hour_12 = hour % 12
    if hour_12 == 0: hour_12 = 12
    return f"{hour_12}:{dt_obj.strftime('%M')} {period}"

@app.route('/', methods=['GET', 'POST'])
def index():
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    # وقت البداية التلقائي (الآن)
    default_start = now.strftime('%H:%M')
    
    results = None
    view_type = request.form.get('view_type', 'main')
    
    # وقت البداية دائماً هو الوقت الحالي (لا يتأثر بالمدخلات ليبقى ثابتاً)
    start_h = default_start
    # وقت النهاية يمكن تعديله من المستخدم
    end_h = request.form.get('end_time', '23:59')

    if request.method == 'POST' and view_type != 'main':
        iso_start = f"{current_date}T{start_h}:00.000+03:00"
        iso_end = f"{current_date}T{end_h}:00.000+03:00"
        
        analyzer = FlightAnalyzer()
        data = analyzer.fetch_data(iso_start, iso_end)
        
        flights_list = []
        hourly_pax = Counter()
        total_pax = 0
        
        for f in data:
            try:
                dt_raw = f.get('EarlyOrDelayedDateTime', '').split('+')[0]
                dt_obj = datetime.fromisoformat(dt_raw)
                
                airline_info = f.get('Airline') or {}
                origin_info = f.get('OriginAirport') or {}
                baggage_info = f.get('BaggageReclaim') or {}

                # حساب الركاب: الطائرات الكبيرة 300، الصغيرة 170
                ac_type = f.get('AircraftType', '')
                pax = 300 if any(x in str(ac_type) for x in ['777', '787', '330', '350', '380']) else 170
                total_pax += pax

                flights_list.append({
                    'flight_full': f"{(airline_info.get('Code') or '')} {(f.get('FlightNumber') or '')}".strip(),
                    'origin_city': origin_info.get('ArabicName') or "غير معروف",
                    'origin_iata': origin_info.get('IataCode') or "???",
                    'time': format_time_12h(dt_obj),
                    'pax': pax,
                    'belt': baggage_info.get('BaggageReclaimId') or "---"
                })
                hourly_pax[dt_obj.hour] += pax
            except: continue

        # حساب الاحتياج (أعلى كثافة ركاب في ساعة واحدة مقسومة على 60)
        needed = math.ceil(max(hourly_pax.values() or [0]) / 60)

        results = {
            'flights': flights_list,
            'total_flights': len(flights_list),
            'total_pax': total_pax,
            'needed_counters': needed
        }

    return render_template('index.html', results=results, start_h=start_h, end_h=end_h, view_type=view_type)

if __name__ == '__main__':
    app.run(debug=True)
