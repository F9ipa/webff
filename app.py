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

    # حساب سعة الركاب بناءً على موديل الطائرة بدقة
    def get_pax_capacity(self, ac_type):
        if not ac_type: return 160
        ac_type = ac_type.upper()
        
        # طائرات عريضة البدن (سعة كبيرة)
        if any(x in ac_type for x in ['777', '77W', '772', '787', '789', '747', '380', '350', '330', '333', '332']):
            return 300
        # طائرات متوسطة (سعة عادية)
        elif any(x in ac_type for x in ['320', '321', '737', '738', 'MAX']):
            return 165
        # طائرات صغيرة
        else:
            return 120

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
        hourly_pax = Counter()
        total_pax = 0
        delayed_count = 0

        for f in data:
            status_code = f.get('PublicRemark', {}).get('Code', '').upper()
            if status_code in ['ARR', 'DLV', 'LND']: continue 
            
            dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_raw)
            
            # حساب الركاب بناءً على نوع الطائرة
            pax = analyzer.get_pax_capacity(f.get('AircraftType'))
            total_pax += pax
            
            # جلب الأسماء بالعربي
            city_ar = f.get('OriginAirportArabicName') or f.get('OriginAirportEnglishName', '')
            country_ar = f.get('OriginCountryArabicName') or f.get('OriginCountryEnglishName', '')
            
            flights_list.append({
                'fn': f.get('FlightNumber'),
                'origin': f"{city_ar} - {country_ar}",
                'time': dt_obj.strftime('%H:%M'),
                'pax': pax,
                'is_delayed': status_code == 'DEL'
            })
            hourly_pax[dt_obj.hour] += pax
            if status_code == 'DEL': delayed_count += 1

        # حساب الاحتياج (كل كاونتر يخدم حوالي 65 مسافر في الساعة)
        needed_counters = math.ceil(max(hourly_pax.values() or [0]) / 65)

        results = {
            'flights': flights_list,
            'count': len(flights_list),
            'total_pax': total_pax,
            'delayed': delayed_count,
            'needed_counters': max(needed_counters, 1),
            'active_counters': active_counters
        }

    return render_template('index.html', results=results, current_date=current_date, 
                           start_h=start_h, end_h=end_h, view_type=view_type)

if __name__ == '__main__':
    app.run(debug=True)
