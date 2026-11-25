from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template_string, flash
from busapp.logic import RouteBook, compute_summary, find_warnings, find_stop_index, to_min, to_hhmm
from busapp.storage import load_routes, save_routes
from busapp.validation import build_route, ValidationError
from busapp.logic import DuplicateRoute

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'routes.json'
app = Flask(__name__)
app.secret_key = 'campus-bus-helper-local'

def get_book():
    routes, _ = load_routes(str(DATA))
    return RouteBook(routes)

def persist(book):
    save_routes(str(DATA), book.all())

BASE = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Campus Bus Route Helper</title>

    <style>
        :root {
            --navy: #10243a;
            --blue: #2563eb;
            --blue-dark: #1d4ed8;
            --bg: #f4f7fb;
            --white: #ffffff;
            --ink: #172b4d;
            --muted: #64748b;
            --border: #e2e8f0;
            --green: #059669;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: var(--bg);
            color: var(--ink);
            font: 15px/1.6 system-ui, -apple-system,
                  BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        a {
            color: var(--blue);
            text-decoration: none;
        }

        a:hover {
            color: var(--blue-dark);
        }

        /* Top navigation */

        .hero {
            background: var(--navy);
            color: white;
            padding: 18px 5%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
            flex-wrap: wrap;
        }

        .hero h1 {
            margin: 0;
            font-size: 22px;
            font-weight: 750;
            letter-spacing: -0.5px;
        }

        .hero p {
            margin: 2px 0 0;
            color: #b9cbe0;
            font-size: 13px;
        }

        .hero h1::before {
            content: "🚌";
            margin-right: 10px;
        }

        .hero::after {
            content: "●  SYSTEM ONLINE";
            color: #86efac;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
        }

        /* Main layout */

        .wrap {
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 24px;
        }

        .nav {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 26px;
            padding: 10px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 14px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03);
        }

        .nav a {
            color: #475569;
            padding: 10px 14px;
            border-radius: 9px;
            font-size: 13px;
            font-weight: 650;
            transition: 0.2s;
        }

        .nav a:hover {
            background: #eff6ff;
            color: var(--blue);
        }

        /* Page headings */

        h2 {
            margin: 0 0 18px;
            font-size: 21px;
            letter-spacing: -0.4px;
        }

        h3 {
            margin: 0 0 14px;
            font-size: 17px;
        }

        /* Cards and dashboard statistics */

        .grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
        }

        .card {
            background: var(--white);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(15, 23, 42, 0.035);
            transition: box-shadow 0.2s, transform 0.2s;
        }

        .card:hover {
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.07);
        }

        .stat {
            font-size: 34px;
            line-height: 1.3;
            font-weight: 800;
            color: var(--navy);
            letter-spacing: -1px;
        }

        .muted {
            color: var(--muted);
        }

        /* Forms */

        .field {
            display: flex;
            flex-direction: column;
            gap: 7px;
            margin-bottom: 16px;
        }

        label {
            font-size: 13px;
            font-weight: 650;
            color: #334155;
        }

        input,
        select,
        textarea {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            background: white;
            color: var(--ink);
            font: inherit;
            outline: none;
            transition: border 0.2s, box-shadow 0.2s;
        }

        input:focus,
        select:focus,
        textarea:focus {
            border-color: var(--blue);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
        }

        /* Buttons */

        .btn {
            display: inline-block;
            padding: 11px 18px;
            background: var(--blue);
            color: white;
            border: 0;
            border-radius: 10px;
            font: inherit;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s, transform 0.2s;
        }

        .btn:hover {
            background: var(--blue-dark);
            color: white;
            transform: translateY(-1px);
        }

        .danger {
            background: #dc2626;
        }

        .danger:hover {
            background: #b91c1c;
        }

        /* Tables */

        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }

        th,
        td {
            text-align: left;
            padding: 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }

        th {
            background: #f8fafc;
            color: #475569;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        tr:hover td {
            background: #f8fbff;
        }

        .routepath {
            color: var(--muted);
            font-size: 13px;
        }

        /* Status indicators */

        .pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 99px;
            background: #dcfce7;
            color: #166534;
            font-size: 12px;
            font-weight: 700;
        }

        .Delayed {
            background: #fef3c7;
            color: #92400e;
        }

        .Suspended {
            background: #fee2e2;
            color: #991b1b;
        }

        .flash {
            padding: 14px 18px;
            background: #eff6ff;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
            border-radius: 12px;
            margin: 12px 0 22px;
        }

        .inline {
            display: inline;
        }

        .small {
            font-size: 13px;
        }

        /* Dashboard introduction */

        .wrap > .grid:first-of-type .card {
            position: relative;
            overflow: hidden;
        }

        .wrap > .grid:first-of-type .card:nth-child(1) {
            border-top: 4px solid #2563eb;
        }

        .wrap > .grid:first-of-type .card:nth-child(2) {
            border-top: 4px solid #059669;
        }

        .wrap > .grid:first-of-type .card:nth-child(3) {
            border-top: 4px solid #7c3aed;
        }

        /* Responsive layout */

        @media (max-width: 700px) {
            .hero {
                padding: 18px 20px;
            }

            .hero h1 {
                font-size: 19px;
            }

            .hero::after {
                font-size: 10px;
            }

            .wrap {
                margin: 18px auto;
                padding: 0 14px;
            }

            .nav {
                gap: 4px;
                padding: 8px;
            }

            .nav a {
                padding: 9px 10px;
                font-size: 12px;
            }

            .card {
                padding: 18px;
            }

            .stat {
                font-size: 29px;
            }

            th,
            td {
                padding: 9px;
                font-size: 12px;
            }
        }
    </style>
</head>

<body>
    <header class="hero">
        <div>
            <h1>Campus Bus Route Helper</h1>
            <p>Find your stop. Find your bus.</p>
        </div>
    </header>

    <main class="wrap">
        <nav class="nav">
            <a href="/">Dashboard</a>
            <a href="/routes">All Routes</a>
            <a href="/search">Search Stop</a>
            <a href="/ride">Find a Ride</a>
            <a href="/next">Next Buses</a>
            <a href="/add">Add Route</a>
            <a href="/summary">Summary</a>
            <a href="/warnings">Warnings</a>
        </nav>

        {% with messages = get_flashed_messages() %}
            {% for message in messages %}
                <div class="flash">{{ message }}</div>
            {% endfor %}
        {% endwith %}

        {{ content|safe }}
    </main>
</body>
</html>
'''

def page(content, **ctx):
    return render_template_string(BASE, content=render_template_string(content, **ctx))

FORM = '''<section class="card"><h2>{{heading}}</h2><form method="post"><div class="grid">
<div class="field"><label>Route ID</label><input name="route_id" required placeholder="R12" value="{{r.route_id if r else ''}}" {% if edit %}readonly{% endif %}></div>
<div class="field"><label>Route name</label><input name="name" required value="{{r.name if r else ''}}"></div>
<div class="field"><label>Stops (separate with commas)</label><input name="stops" required placeholder="Main Gate, Library, Hostel" value="{{r.stops|join(', ') if r else ''}}"></div>
<div class="field"><label>First departure</label><input name="start_time" type="time" required value="{{r.start_time if r else '07:00'}}"></div>
<div class="field"><label>Last departure</label><input name="end_time" type="time" required value="{{r.end_time if r else '20:00'}}"></div>
<div class="field"><label>Interval (minutes)</label><input name="interval_min" type="number" min="1" max="120" required value="{{r.interval_min if r else 20}}"></div>
<div class="field"><label>Seats</label><input name="capacity" type="number" min="10" max="120" required value="{{r.capacity if r else 40}}"></div>
<div class="field"><label>Status</label><select name="status">{% for s in ['Active','Delayed','Suspended'] %}<option {% if r and r.status==s %}selected{% endif %}>{{s}}</option>{% endfor %}</select></div></div><button class="btn">Save route</button> <a href="/routes">Cancel</a></form></section>'''

@app.route('/')
def home():
    book=get_book(); routes=book.all()
    content='''<div class="grid"><section class="card"><div class="muted">Routes in system</div><div class="stat">{{n}}</div></section><section class="card"><div class="muted">Active routes</div><div class="stat">{{active}}</div></section><section class="card"><div class="muted">Stops served</div><div class="stat">{{stops}}</div></section></div><section class="card"><h2>Quick find</h2><form action="/search" method="get"><div class="field"><label>Stop name</label><input name="q" placeholder="Type a stop name" required></div><button class="btn">Search routes</button></form></section><section class="card"><h2>Recent route list</h2><p class="muted">Browse routes, find a bus between two stops, or check upcoming departures.</p><a class="btn" href="/routes">View all routes</a></section>'''
    stops={s.casefold() for r in routes for s in r.stops}
    return page(content,n=len(routes),active=sum(r.status=='Active' for r in routes),stops=len(stops))

@app.route('/routes')
def routes_page():
    book=get_book(); routes=book.all()
    content='''<section class="card"><h2>All routes ({{routes|length}})</h2><div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>Route</th><th>Stops</th><th>Service</th><th>Status</th><th>Actions</th></tr></thead><tbody>{% for r in routes %}<tr><td>{{r.route_id}}</td><td><b>{{r.name}}</b><br><span class="routepath">{{r.stops|join(' → ')}}</span></td><td>{{r.stops|length}}</td><td>{{r.start_time}}–{{r.end_time}}<br>Every {{r.interval_min}} min · {{r.capacity}} seats</td><td><span class="pill {{r.status}}">{{r.status}}</span></td><td><a href="/edit/{{r.route_id}}">Edit</a><form class="inline" method="post" action="/delete/{{r.route_id}}" onsubmit="return confirm('Delete this route?')"><button class="btn danger small">Delete</button></form></td></tr>{% endfor %}</tbody></table></div></section>'''
    return page(content,routes=routes)

@app.route('/add',methods=['GET','POST'])
def add():
    if request.method=='POST':
        try:
            r=build_route(request.form); book=get_book(); book.add(r); persist(book); flash('Route added and saved.')
            return redirect(url_for('routes_page'))
        except (ValidationError,DuplicateRoute) as e: flash(str(e))
    return page(FORM,heading='Add a route',r=None,edit=False)

@app.route('/edit/<route_id>',methods=['GET','POST'])
def edit(route_id):
    book=get_book(); old=book.get(route_id)
    if not old: flash('Route not found.'); return redirect(url_for('routes_page'))
    if request.method=='POST':
        try:
            fields=request.form.to_dict(); fields['route_id']=old.route_id
            r=build_route(fields); book.replace(r); persist(book); flash('Route updated and saved.')
            return redirect(url_for('routes_page'))
        except ValidationError as e: flash(str(e))
    return page(FORM,heading='Edit route '+old.route_id,r=old,edit=True)

@app.post('/delete/<route_id>')
def delete(route_id):
    book=get_book(); book.remove(route_id); persist(book); flash('Route deleted.')
    return redirect(url_for('routes_page'))

@app.route('/search')
def search():
    q=request.args.get('q','').strip(); results=get_book().search_stop(q) if q else []
    content='''<section class="card"><h2>Search by stop</h2><form><div class="field"><label>Stop name</label><input name="q" value="{{q}}" placeholder="e.g. Main Gate"></div><button class="btn">Search</button></form></section>{% if q %}<section class="card"><h3>Results for “{{q}}”</h3>{% if results %}<ul>{% for r,hits in results %}<li><b>{{r.route_id}} — {{r.name}}</b> ({{r.status}})<br><span class="routepath">{{r.stops|join(' → ')}}</span></li>{% endfor %}</ul>{% else %}<p>No matching routes found.</p>{% endif %}</section>{% endif %}'''
    return page(content,q=q,results=results)

@app.route('/ride',methods=['GET','POST'])
def ride():
    origin=request.values.get('origin','').strip(); dest=request.values.get('dest','').strip(); results=get_book().connecting(origin,dest) if origin and dest else []
    content='''<section class="card"><h2>Find a ride</h2><form><div class="grid"><div class="field"><label>From</label><input name="origin" required value="{{origin}}" placeholder="Starting stop"></div><div class="field"><label>To</label><input name="dest" required value="{{dest}}" placeholder="Destination"></div></div><button class="btn">Find buses</button></form></section>{% if origin and dest %}<section class="card"><h3>{{results|length}} route(s) from {{origin}} to {{dest}}</h3>{% if results %}<ul>{% for r,i,j,mins in results %}<li><b>{{r.route_id}} — {{r.name}}</b> · approx. {{mins}} min between stops<br><span class="routepath">{{r.stops[i:j+1]|join(' → ')}}</span></li>{% endfor %}</ul><p class="muted small">Travel time is an estimate based on 3 minutes between stops.</p>{% else %}<p>No route found in that direction.</p>{% endif %}</section>{% endif %}'''
    return page(content,origin=origin,dest=dest,results=results)

@app.route('/next',methods=['GET','POST'])
def next_buses():
    stop=request.values.get('stop','').strip(); after=request.values.get('after','08:00').strip(); results=[]
    try: after_min=to_min(after)
    except Exception: after_min=8*60; after='08:00'
    if stop:
        book=get_book()
        for r in book.all():
            idx=find_stop_index(r.stops,stop)
            if idx is not None:
                times=book.next_buses(r,idx,after_min,3)
                if times: results.append((r,r.stops[idx],', '.join(to_hhmm(t) for t in times)))
    content='''<section class="card"><h2>Next buses at a stop</h2><form><div class="grid"><div class="field"><label>Stop name</label><input name="stop" value="{{stop}}" required></div><div class="field"><label>Show departures after</label><input type="time" name="after" value="{{after}}" required></div></div><button class="btn">Check departures</button></form></section>{% if stop %}<section class="card"><h3>Upcoming buses</h3>{% if results %}<table><tr><th>Route</th><th>Stop</th><th>Next departures</th></tr>{% for r,s,times in results %}<tr><td>{{r.route_id}} — {{r.name}}</td><td>{{s}}</td><td>{{times}}</td></tr>{% endfor %}</table>{% else %}<p>No upcoming departures found for this stop and time.</p>{% endif %}<p class="muted small">Departure estimates use the project's 3-minute-per-stop assumption.</p></section>{% endif %}'''
    return page(content,stop=stop,after=after,results=results)

@app.route('/summary')
def summary():
    data=compute_summary(get_book())
    content='''<section class="card"><h2>Summary report</h2>{% if data.total %}<div class="grid">{% for label,key in [('Total routes','total'),('Unique stops','unique_stops'),('Daily trips','daily_trips'),('Daily seat capacity','daily_seats')] %}<div class="card"><div class="muted">{{label}}</div><div class="stat">{{data.get(key,'—')|round(1)}}</div></div>{% endfor %}</div><p>Average interval: {{data.avg_interval|round(1)}} min · Average stops per route: {{data.avg_stops|round(1)}} · Average seats: {{data.avg_capacity|round(1)}}</p><h3>Most-served stops</h3><ol>{% for stop,count in data.top_stops %}<li>{{stop}} — {{count}} routes</li>{% endfor %}</ol>{% else %}<p>No routes yet.</p>{% endif %}</section>'''
    return page(content,data=data)

@app.route('/warnings')
def warnings():
    items=find_warnings(get_book())
    content='''<section class="card"><h2>Route warnings</h2>{% if items %}<ul>{% for level,msg in items %}<li><b>{{level}}</b> — {{msg}}</li>{% endfor %}</ul>{% else %}<p>No warnings. All routes look good.</p>{% endif %}</section>'''
    return page(content,items=items)

if __name__ == '__main__':
    print('Campus Bus Route Helper is available at http://127.0.0.1:5000')
    app.run(debug=False, host='127.0.0.1', port=5000)
