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

    # تقدير ركاب الطائرة بناءً على النوع (تقريبي)
    def estimate_capacity(self, aircraft_type):
        if not aircraft_type: return 150
        large = ['777', '787', '330', '350', '380', '747']
        return 300 if any(x in aircraft_type for x in large) else 160

    def fetch_data(self, start_dt, end_dt):
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {start_dt} and EarlyOrDelayedDateTime lt {end_dt}) and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')",
            "$orderby": "EarlyOrDelayedDateTime",
            "$count": "true"
        }
        try:
            response = requests.get(self.url, params=params, headers=self.headers, timeout=10)
            return response.json().get('value', [])
        except:
            return []

@app.route('/', methods=['GET', 'POST'])
def index():
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    results = None
    
    # الحصول على المدخلات من الفورم
    start_h = request.form.get('start_time', '00:00')
    end_h = request.form.get('end_time', '23:59')
    active_counters = request.form.get('active_counters', type=int) or 0
    view_type = request.form.get('view_type', 'main') # لتحديد أي صفحة تظهر

    if request.method == 'POST' and view_type != 'main':
        iso_start = f"{current_date}T{start_h}:00.000+03:00"
        iso_end = f"{current_date}T{end_h}:00.000+03:00"
        limit_end_dt = datetime.fromisoformat(f"{current_date}T{end_h}")

        analyzer = FlightAnalyzer()
        data = analyzer.fetch_data(iso_start, iso_end)
        
        flights_list = []
        hourly_stats = Counter()
        hourly_pax = Counter()
        total_pax = 0
        delayed_count = 0

        for f in data:
            status_code = f.get('PublicRemark', {}).get('Code', '').upper()
            if status_code in ['ARR', 'DLV', 'LND']: continue 
            
            dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_raw)
            if dt_obj >= limit_end_dt: continue

            pax = analyzer.estimate_capacity(f.get('AircraftType'))
            total_pax += pax
            
            flights_list.append({
                'fn': f.get('FlightNumber'),
                'origin': f.get('OriginAirportEnglishName'),
                'time': dt_obj.strftime('%H:%M'),
                'pax': pax,
                'is_delayed': status_code == 'DEL'
            })
            
            hourly_stats[dt_obj.hour] += 1
            hourly_pax[dt_obj.hour] += pax
            if status_code == 'DEL': delayed_count += 1

        # حساب الفجوات
        flight_times = sorted([datetime.strptime(f['time'], '%H:%M') for f in flights_list])
        gaps = []
        for i in range(len(flight_times) - 1):
            diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
            if diff > 15:
                gaps.append({'from': flight_times[i].strftime('%H:%M'), 'to': flight_times[i+1].strftime('%H:%M'), 'duration': int(diff)})

        # حساب الذروة
        peak_results = None
        if hourly_stats:
            p_hour = max(hourly_stats, key=hourly_stats.get)
            peak_results = {'start': f"{p_hour:02d}:00", 'end': f"{p_hour+1:02d}:00", 'count': hourly_stats[p_hour]}

        # تحليل الكاونترات (الاحتياج)
        max_hourly_pax = max(hourly_pax.values()) if hourly_pax else 0
        needed_counters = math.ceil(max_hourly_pax / 60) # افتراض كاونتر لكل 60 مسافر/ساعة

        results = {
            'flights': flights_list,
            'count': len(flights_list),
            'total_pax': total_pax,
            'delayed': delayed_count,
            'gaps': gaps,
            'peak': peak_results,
            'needed_counters': needed_counters,
            'active_counters': active_counters
        }

    return render_template('index.html', results=results, current_date=current_date, start_h=start_h, end_h=end_h, view_type=view_type)

if __name__ == '__main__':
    app.run(debug=True)
