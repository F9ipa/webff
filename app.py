from flask import Flask, render_template, request
import requests
from datetime import datetime
from collections import Counter

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
        except:
            return []

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    now = datetime.now()
    # التاريخ تلقائي اليوم
    current_date = now.strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        start_h = request.form.get('start_time', '13:00')
        end_h = request.form.get('end_time', '23:59')
        
        iso_start = f"{current_date}T{start_h}:00.000+03:00"
        iso_end = f"{current_date}T{end_h}:00.000+03:00"
        limit_end_dt = datetime.fromisoformat(f"{current_date}T{end_h}")

        analyzer = FlightAnalyzer()
        data = analyzer.fetch_data(iso_start, iso_end)
        
        flight_times = []
        delayed_count = 0
        for f in data:
            status_code = f.get('PublicRemark', {}).get('Code', '').upper()
            if status_code in ['ARR', 'DLV', 'LND']: continue
            
            dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_raw)
            if dt_obj >= limit_end_dt: continue
            
            flight_times.append(dt_obj)
            if status_code == 'DEL': delayed_count += 1

        flight_times.sort()
        gaps = []
        for i in range(len(flight_times) - 1):
            diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
            if diff > 15:
                gaps.append({'from': flight_times[i].strftime('%H:%M'), 'to': flight_times[i+1].strftime('%H:%M'), 'duration': int(diff)})

        results = {
            'date': current_date,
            'count': len(flight_times),
            'delayed': delayed_count,
            'gaps': gaps
        }

    return render_template('index.html', results=results, current_date=current_date)

if __name__ == '__main__':
    app.run(debug=True)
