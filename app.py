from flask import Flask, render_template, request
import requests
from datetime import datetime
from collections import Counter
import math

app = Flask(__name__)

class FlightAnalyzer:
    def __init__(self):
        # الرابط الرسمي لـ API مطار الملك عبدالعزيز
        self.url = "https://www.kaia.sa/ext-api/flightsearch/flights"
        self.headers = {
            "Accept": "application/json",
            "Authorization": "Basic dGVzdGVyOlRoZVMzY3JldA==",
            "User-Agent": "Mozilla/5.0"
        }

    def fetch_data(self, start_dt, end_dt):
        # الفلترة المطلوبة: الرحلات الدولية القادمة لصالة 1
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {start_dt} and EarlyOrDelayedDateTime lt {end_dt}) and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')",
            "$orderby": "EarlyOrDelayedDateTime",
            "$count": "true"
        }
        try:
            response = requests.get(self.url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json().get('value', [])
            return []
        except:
            return []

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
            try:
                # معالجة الوقت
                dt_raw = f.get('EarlyOrDelayedDateTime', '').split('+')[0]
                dt_obj = datetime.fromisoformat(dt_raw)
                
                # استخراج البيانات من الكائنات المتداخلة (Objects) لضمان ظهورها
                airline_info = f.get('Airline') or {}
                origin_info = f.get('OriginAirport') or {}
                baggage_info = f.get('BaggageReclaim') or {}

                # 1. رمز الطيران ورقم الرحلة
                a_code = airline_info.get('Code') or f.get('AirlineCode') or ""
                f_num = f.get('FlightNumber') or ""
                
                # 2. جهة القدوم (المدينة والرمز)
                city_ar = origin_info.get('ArabicName') or f.get('OriginAirportArabicName') or "غير معروف"
                iata = origin_info.get('IataCode') or f.get('OriginAirportIataCode') or "???"
                
                # 3. سير الشنط
                belt = baggage_info.get('BaggageReclaimId') or "---"

                # حساب الركاب التقديري بناءً على نوع الطائرة
                ac_type = f.get('AircraftType', '')
                pax = 300 if any(x in str(ac_type) for x in ['777', '787', '330', '350', '380']) else 170

                flights_list.append({
                    'flight_full': f"{a_code} {f_num}".strip(),
                    'origin_city': city_ar,
                    'origin_iata': iata,
                    'time': dt_obj.strftime('%H:%M'),
                    'pax': pax,
                    'belt': belt,
                    'ac': ac_type
                })
                
                hourly_stats[dt_obj.hour] += 1
                hourly_pax[dt_obj.hour] += pax
                flight_objects.append(dt_obj)
            except:
                continue

        # تحليل الفجوات والذروة
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
            'gaps': gaps,
            'peak': peak_info,
            'needed_counters': math.ceil(max(hourly_pax.values() or [0]) / 60),
            'max_pax': max(hourly_pax.values() or [0]),
            'active_counters': active_counters
        }

    return render_template('index.html', results=results, current_date=current_date, start_h=start_h, end_h=end_h, view_type=view_type)

if __name__ == '__main__':
    app.run(debug=True)
