"""
build_dataset.py
Generates flights.csv -- a realistic, directed flight network across 70+ cities.

Design notes
------------
* Each city has real (approx.) coordinates; great-circle distance drives fare
  and flight time, so the numbers are physically plausible.
* The network is hub-and-spoke: spokes connect to their nearest hubs, hubs
  connect to each other, and nearby cities get regional short-haul links.
* Every link is emitted in BOTH directions as separate rows (a real flight
  network is directed -- the outbound and return legs differ in price/time).
* A handful of thin ultra-long-haul routes are marked "premium nonstop":
  expensive but fast. That guarantees cases where the cheapest route needs a
  connection while the fastest route is the pricey direct flight -- the exact
  trade-off the optimizer exists to resolve.

Run:  python build_dataset.py     ->  writes flights.csv
"""
import csv, math, random
from collections import defaultdict

random.seed(42)

# ---------------------------------------------------------------- cities
# code, name, country, lat, lon, region
CITIES = [
    ("DEL","Delhi","India",28.6139,77.2090,"India"),
    ("BOM","Mumbai","India",19.0896,72.8656,"India"),
    ("BLR","Bengaluru","India",13.1986,77.7066,"India"),
    ("MAA","Chennai","India",12.9941,80.1709,"India"),
    ("CCU","Kolkata","India",22.6547,88.4467,"India"),
    ("HYD","Hyderabad","India",17.2403,78.4294,"India"),
    ("COK","Kochi","India",10.1520,76.4019,"India"),
    ("AMD","Ahmedabad","India",23.0734,72.6266,"India"),
    ("GOI","Goa","India",15.3808,73.8314,"India"),
    ("PNQ","Pune","India",18.5821,73.9197,"India"),
    ("JAI","Jaipur","India",26.8242,75.8122,"India"),
    ("LKO","Lucknow","India",26.7606,80.8893,"India"),
    ("TRV","Thiruvananthapuram","India",8.4821,76.9200,"India"),
    ("IXC","Chandigarh","India",30.6735,76.7885,"India"),
    ("GAU","Guwahati","India",26.1061,91.5859,"India"),
    ("DXB","Dubai","United Arab Emirates",25.2532,55.3657,"MiddleEast"),
    ("AUH","Abu Dhabi","United Arab Emirates",24.4330,54.6511,"MiddleEast"),
    ("DOH","Doha","Qatar",25.2731,51.6081,"MiddleEast"),
    ("RUH","Riyadh","Saudi Arabia",24.9576,46.6988,"MiddleEast"),
    ("JED","Jeddah","Saudi Arabia",21.6796,39.1565,"MiddleEast"),
    ("MCT","Muscat","Oman",23.5933,58.2844,"MiddleEast"),
    ("KWI","Kuwait City","Kuwait",29.2266,47.9689,"MiddleEast"),
    ("BAH","Bahrain","Bahrain",26.2708,50.6336,"MiddleEast"),
    ("LHR","London","United Kingdom",51.4700,-0.4543,"Europe"),
    ("CDG","Paris","France",49.0097,2.5479,"Europe"),
    ("FRA","Frankfurt","Germany",50.0379,8.5622,"Europe"),
    ("AMS","Amsterdam","Netherlands",52.3105,4.7683,"Europe"),
    ("IST","Istanbul","Turkey",41.2753,28.7519,"Europe"),
    ("MAD","Madrid","Spain",40.4983,-3.5676,"Europe"),
    ("FCO","Rome","Italy",41.8003,12.2389,"Europe"),
    ("ZRH","Zurich","Switzerland",47.4647,8.5492,"Europe"),
    ("VIE","Vienna","Austria",48.1103,16.5697,"Europe"),
    ("CPH","Copenhagen","Denmark",55.6180,12.6508,"Europe"),
    ("ARN","Stockholm","Sweden",59.6519,17.9186,"Europe"),
    ("DUB","Dublin","Ireland",53.4213,-6.2701,"Europe"),
    ("LIS","Lisbon","Portugal",38.7742,-9.1342,"Europe"),
    ("JFK","New York","United States",40.6413,-73.7781,"NorthAmerica"),
    ("LAX","Los Angeles","United States",33.9416,-118.4085,"NorthAmerica"),
    ("ORD","Chicago","United States",41.9742,-87.9073,"NorthAmerica"),
    ("YYZ","Toronto","Canada",43.6777,-79.6248,"NorthAmerica"),
    ("YVR","Vancouver","Canada",49.1967,-123.1815,"NorthAmerica"),
    ("SFO","San Francisco","United States",37.6213,-122.3790,"NorthAmerica"),
    ("MIA","Miami","United States",25.7959,-80.2870,"NorthAmerica"),
    ("DFW","Dallas","United States",32.8998,-97.0403,"NorthAmerica"),
    ("MEX","Mexico City","Mexico",19.4361,-99.0719,"NorthAmerica"),
    ("GRU","Sao Paulo","Brazil",-23.4356,-46.4731,"SouthAmerica"),
    ("EZE","Buenos Aires","Argentina",-34.8222,-58.5358,"SouthAmerica"),
    ("BOG","Bogota","Colombia",4.7016,-74.1469,"SouthAmerica"),
    ("LIM","Lima","Peru",-12.0219,-77.1143,"SouthAmerica"),
    ("SIN","Singapore","Singapore",1.3644,103.9915,"AsiaPacific"),
    ("BKK","Bangkok","Thailand",13.6900,100.7501,"AsiaPacific"),
    ("KUL","Kuala Lumpur","Malaysia",2.7456,101.7099,"AsiaPacific"),
    ("HKG","Hong Kong","Hong Kong",22.3080,113.9185,"AsiaPacific"),
    ("NRT","Tokyo","Japan",35.7720,140.3929,"AsiaPacific"),
    ("ICN","Seoul","South Korea",37.4602,126.4407,"AsiaPacific"),
    ("PEK","Beijing","China",40.0799,116.6031,"AsiaPacific"),
    ("PVG","Shanghai","China",31.1443,121.8083,"AsiaPacific"),
    ("TPE","Taipei","Taiwan",25.0777,121.2328,"AsiaPacific"),
    ("MNL","Manila","Philippines",14.5086,121.0194,"AsiaPacific"),
    ("CGK","Jakarta","Indonesia",-6.1256,106.6559,"AsiaPacific"),
    ("HAN","Hanoi","Vietnam",21.2212,105.8072,"AsiaPacific"),
    ("SYD","Sydney","Australia",-33.9399,151.1753,"AsiaPacific"),
    ("MEL","Melbourne","Australia",-37.6690,144.8410,"AsiaPacific"),
    ("AKL","Auckland","New Zealand",-37.0082,174.7850,"AsiaPacific"),
    ("JNB","Johannesburg","South Africa",-26.1392,28.2460,"Africa"),
    ("CPT","Cape Town","South Africa",-33.9715,18.6021,"Africa"),
    ("CAI","Cairo","Egypt",30.1219,31.4056,"Africa"),
    ("NBO","Nairobi","Kenya",-1.3192,36.9278,"Africa"),
    ("LOS","Lagos","Nigeria",6.5774,3.3212,"Africa"),
]

HUBS = {"DEL","BOM","DXB","DOH","IST","LHR","FRA","CDG","JFK","SIN","HKG","NRT","SYD","JNB","GRU","LAX","YYZ","CAI","BKK","KUL"}
AIRLINES = ["AirIndia","IndiGo","Emirates","Qatar","Etihad","Lufthansa","BritishAirways","KLM","Turkish","Singapore","Cathay","Qantas","Delta","United","AirFrance","Thai","Malaysia","Ethiopian","SouthAfrican","LATAM"]

# ---------------------------------------------------------------- geometry
def haversine(a, b):
    (_, _, _, la1, lo1, _), (_, _, _, la2, lo2, _) = a, b
    R = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp = math.radians(la2 - la1); dl = math.radians(lo2 - lo1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))

C = {c[0]: c for c in CITIES}
DIST = {}
def dist(a, b):
    k = tuple(sorted((a, b)))
    if k not in DIST:
        DIST[k] = haversine(C[a], C[b])
    return DIST[k]

def nearest(code, pool, n):
    return [x for x in sorted(pool, key=lambda o: dist(code, o) if o != code else 9e9) if x != code][:n]

# ---------------------------------------------------------------- build pairs
pairs = set()  # unordered {a,b}
def link(a, b):
    if a != b:
        pairs.add(tuple(sorted((a, b))))

codes = [c[0] for c in CITIES]
for code in codes:
    if code in HUBS:
        for h in nearest(code, HUBS, 5):          # hub <-> hub trunk routes
            link(code, h)
    else:
        for h in nearest(code, HUBS, 3):          # spoke -> nearest hubs
            link(code, h)

by_region = defaultdict(list)
for c in CITIES:
    by_region[c[5]].append(c[0])
for code in codes:                                # regional short-haul
    for r in nearest(code, by_region[C[code][5]], 2):
        link(code, r)

# premium ultra-long-haul nonstops (expensive, fast)
PREMIUM = [("DEL","JFK"),("DEL","YYZ"),("DEL","SFO"),("DEL","LAX"),("BOM","JFK"),
           ("BLR","SFO"),("MAA","SFO"),("DEL","GRU"),("DEL","SYD"),("BOM","SYD"),
           ("DEL","ORD"),("BOM","YVR")]
premium_pairs = {tuple(sorted(p)) for p in PREMIUM}
for a, b in PREMIUM:
    link(a, b)

# ---------------------------------------------------------------- emit rows
def fare(km, a, b, hub_hub, air):
    base = 650.0
    rate = 2.85 if hub_hub else 3.9          # trunk routes are cheaper per km
    f = base + rate * km
    f *= {"AirIndia":1.05,"IndiGo":0.86,"Emirates":1.18,"Qatar":1.14,"Etihad":1.12,
          "Lufthansa":1.22,"BritishAirways":1.24,"KLM":1.2,"Turkish":1.06,
          "Singapore":1.16,"Cathay":1.15,"Qantas":1.2,"Delta":1.08,"United":1.1,
          "AirFrance":1.2,"Thai":1.0,"Malaysia":0.95,"Ethiopian":0.9,
          "SouthAfrican":0.98,"LATAM":0.96}[air]
    f *= random.uniform(0.95, 1.08)
    return int(round(f / 50.0) * 50)

def duration(km):
    return int(round(35 + km / 13.2 + random.uniform(-6, 12)))

rows = []
for a, b in sorted(pairs):
    km = dist(a, b)
    hub_hub = a in HUBS and b in HUBS
    prem = tuple(sorted((a, b))) in premium_pairs
    # outbound and return as independent directed legs
    for src, dst in ((a, b), (b, a)):
        air = random.choice(AIRLINES)
        d = duration(km)
        p = fare(km, a, b, hub_hub, air)
        if prem:                      # premium nonstop: ~2.4x price, a bit faster
            p = int(round(p * 2.4 / 50.0) * 50)
            d = int(round(d * 0.86))
            air = random.choice(["AirIndia","Emirates","United","Qantas","BritishAirways"])
        rows.append([src, dst, air, p, d, int(round(km))])

rows.sort(key=lambda r: (r[0], r[1]))
with open("flights.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["source","destination","airline","price_inr","duration_min","distance_km"])
    w.writerows(rows)

with open("cities.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["code", "name", "country", "latitude", "longitude", "region"])
    w.writerows(CITIES)

print(f"cities : {len(CITIES)}")
print(f"routes : {len(rows)} directed legs  ({len(pairs)} city-pairs)")
print(f"premium nonstop pairs: {len(premium_pairs)}")
