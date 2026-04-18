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

    def get_dynamic_capacity(self, ac_type):
        if not ac_type: return 165
        ac = str(ac_type).upper()
        if any(x in ac for x in ['777', '787', '330', '350', '747', '380']): return 300
        if any(x in ac for x in ['320', '321', '737', 'MAX']): return 170
        return 160

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

@app.route('/', methods=['GET', 'POST'])
def index():
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    results = None
    
    view_type = request.form.get('view_type', 'main')
    start_h = request.form.get('start_time', '00:00')
    end_h = request.form.get('end_time', '23:59')
    active_counters = request.form.get('active_counters', type=int) or 0

    if request.method == 'POST' and view_type != 'main':
        iso_start = f"{current_date}T{start_h}:00.000+03:00"
        iso_end = f"{current_date}T{end_h}:00.000+03:00"
        
        analyzer = FlightAnalyzer()
        data = analyzer.fetch_data(iso_start, iso_end)
        
        flights_list = []
        hourly_stats = Counter()
        hourly_pax = Counter()
        flight_objects = []

        for f in data:
            status_code = f.get('PublicRemark', {}).get('Code', '').upper()
            if status_code in ['ARR', 'DLV', 'LND']: continue 
            
            dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_raw)
            pax = analyzer.get_dynamic_capacity(f.get('AircraftType'))
            
            # --- التعديلات الجديدة بناءً على الـ API ---
            airline = f.get('AirlineCode', '')
            f_num = f.get('FlightNumber', '')
            belt = f.get('BaggageReclaim', {}).get('BaggageReclaimId') or '---'
            
            flights_list.append({
                'flight_full': f"{airline}{f_num}", # رمز الطيران + الرقم
                'origin_city': f.get('OriginAirportArabicName') or "غير معروف",
                'origin_iata': f.get('OriginAirportIataCode') or "???",
                'time': dt_obj.strftime('%H:%M'),
                'pax': pax,
                'belt': belt, # مسار الأمتعة
                'ac': f.get('AircraftType', '')
            })
            
            hourly_stats[dt_obj.hour] += 1
            hourly_pax[dt_obj.hour] += pax
            flight_objects.append(dt_obj)

        flight_objects.sort()
        gaps = []
        for i in range(len(flight_objects) - 1):
            diff = (flight_objects[i+1] - flight_objects[i]).total_seconds() / 60
            if diff > 15:
                gaps.append({'from': flight_objects[i].strftime('%H:%M'), 'to': flight_objects[i+1].strftime('%H:%M'), 'duration': int(diff)})

        peak_info = None
        if hourly_stats:
            p_hour = max(hourly_stats, key=hourly_stats.get)
            peak_info = {'start': f"{p_hour:02d}:00", 'end': f"{p_hour+1:02d}:00", 'count': hourly_stats[p_hour]}

        results = {
            'flights': flights_list,
            'count': len(flights_list),
            'total_pax': sum(hourly_pax.values()),
            'gaps': gaps,
            'peak': peak_info,
            'needed_counters': math.ceil(max(hourly_pax.values() or [0]) / 60),
            'active_counters': active_counters
        }

    return render_template('index.html', results=results, current_date=current_date, start_h=start_h, end_h=end_h, view_type=view_type)

if __name__ == '__main__':
    app.run(debug=True)
