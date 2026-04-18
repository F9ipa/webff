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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_data(self, start_dt, end_dt):
        # تصفية: وصول، صالة 1، دولي، ضمن الوقت المحدد
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {start_dt} and EarlyOrDelayedDateTime lt {end_dt}) and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')",
            "$orderby": "EarlyOrDelayedDateTime",
            "$count": "true"
        }
        try:
            response = requests.get(self.url, params=params, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json().get('value', [])
            return []
        except Exception as e:
            print(f"API Error: {e}")
            return []

def format_time_12h(dt_obj):
    if not dt_obj: return "--:--"
    hour = dt_obj.hour
    period = "م" if hour >= 12 else "ص"
    hour_12 = hour % 12
    if hour_12 == 0: hour_12 = 12
    return f"{hour_12}:{dt_obj.strftime('%M')} {period}"

@app.route('/', methods=['GET', 'POST'])
def index():
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    
    results = None
    view_type = request.form.get('view_type', 'main')
    start_h = request.form.get('start_time', now.strftime('%H:%M'))
    end_h = request.form.get('end_time', '23:59')

    if request.method == 'POST' and view_type != 'main':
        iso_start = f"{current_date}T{start_h}:00.000+03:00"
        iso_end = f"{current_date}T{end_h}:00.000+03:00"
        
        analyzer = FlightAnalyzer()
        data = analyzer.fetch_data(iso_start, iso_end)
        
        flights_list = []
        hourly_stats = Counter()
        hourly_pax = Counter()
        total_pax = 0
        flight_objects = []

        for f in data:
            try:
                dt_str = f.get('EarlyOrDelayedDateTime')
                if not dt_str: continue
                dt_raw = dt_str.split('+')[0]
                dt_obj = datetime.fromisoformat(dt_raw)
                
                # استخراج معلومات الطيران بمرونة عالية
                airline = f.get('Airline') or {}
                origin = f.get('OriginAirport') or {}
                
                # دمج رمز الشركة مع الرقم (مثال: SV 0256)
                airline_code = airline.get('Code') or "---"
                flight_no = f.get('FlightNumber') or ""
                
                # جلب المدينة (الإنجليزية أضمن للظهور)
                city = origin.get('EnglishName') or origin.get('Name') or "Unknown"
                iata = origin.get('IataCode') or "???"

                # تقدير الركاب حسب نوع الطائرة
                ac_type = str(f.get('AircraftType', ''))
                pax = 300 if any(x in ac_type for x in ['777', '787', '330', '350', '380']) else 170
                total_pax += pax

                flights_list.append({
                    'flight_full': f"{airline_code} {flight_no}",
                    'origin_city': city,
                    'origin_iata': iata,
                    'time': format_time_12h(dt_obj),
                    'pax': pax,
                    'status': f.get('PublicRemark', {}).get('EnglishText') or "Scheduled"
                })
                
                hourly_stats[dt_obj.hour] += 1
                hourly_pax[dt_obj.hour] += pax
                flight_objects.append(dt_obj)
            except: continue

        # تحليل الذروة
        peak_info = None
        if hourly_stats:
            p_hour = max(hourly_stats, key=hourly_stats.get)
            peak_info = {
                'start': format_time_12h(datetime.strptime(f"{p_hour}:00", "%H:%M")),
                'end': format_time_12h(datetime.strptime(f"{(p_hour+1)%24}:00", "%H:%M")),
                'count': hourly_stats[p_hour]
            }

        # تحليل الفجوات
        flight_objects.sort()
        gaps = []
        for i in range(len(flight_objects) - 1):
            diff = (flight_objects[i+1] - flight_objects[i]).total_seconds() / 60
            if diff > 15:
                gaps.append({'from': format_time_12h(flight_objects[i]), 'to': format_time_12h(flight_objects[i+1]), 'duration': int(diff)})

        results = {
            'flights': flights_list,
            'total_flights': len(flights_list),
            'total_pax': total_pax,
            'gaps': gaps,
            'peak': peak_info,
            'needed_counters': math.ceil(max(hourly_pax.values() or [0]) / 60)
        }

    return render_template('index.html', results=results, start_h=start_h, end_h=end_h, view_type=view_type)

if __name__ == '__main__':
    app.run(debug=True)
