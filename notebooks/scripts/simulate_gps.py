import json, math, random
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from collections import defaultdict

from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaProducer, KafkaClient
from kafka.errors import TopicAlreadyExistsError
import json

# Kafka related constants
RUNNING_INSIDE_DOCKER = True

if RUNNING_INSIDE_DOCKER:
    KAFKA_BOOTSTRAP_SERVERS = 'kafka:29092'
else:
    KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'


TOPIC = "gps"

DEFAULT_PARTITIONS=3
DEFAULT_REPLICATION_FACTOR=1


# Simulation related constants
ROUTES = "bus_routes.json"
seq = defaultdict(int)

SIM_START = datetime.now(timezone.utc)+timedelta(days=30)
SIM_MINUTES = 1500
DT_SEC = 15

USE_PEAK = True

BASE_SPEED_MPS = 8.34      
SPEED_NOISE_SIGMA = 0.5 
MIN_SPEED_MPS = 1.0

EMIT_SAMPLES=5


SEED = 7
random.seed(SEED)

# Kafka Related Functions
def create_topics():

    print(F"Connecting to Kafka client at {KAFKA_BOOTSTRAP_SERVERS}")
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
        )
        print("Connected to kafka")
    except Exception as e:
        print(f"Failed to conenct: {e}")
        return
    
    try:
        topic = NewTopic(name=TOPIC, num_partitions=DEFAULT_PARTITIONS, replication_factor=DEFAULT_REPLICATION_FACTOR)
        admin_client.create_topics(new_topics=[topic], validate_only=False)
        print(f"Toipic {TOPIC} created")
    except TopicAlreadyExistsError:
        print("Some topics already exists")
    except Exception as e:
        print(f"Failed to create topics: {e}\n")
        return

def get_producer():

    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            acks="all",                     
            retries=1000000,                
            retry_backoff_ms=200,          
            batch_size=64_000,              
            compression_type="lz4",        
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print(f"Producer connected to kafka at {KAFKA_BOOTSTRAP_SERVERS}")
        return producer
    except Exception as e:
        print(f"Failed to create kafka producer: {e}")
        return None


def write_to_kafka(producer, ts_iso, route_id, vehicle_id, direction, lat, lon, speed_mps):
    key = f"{route_id}:{direction}"
    value = {
        "timestamp": ts_iso,
        "route_id": route_id,
        "vehicle_id": vehicle_id,
        "direction": direction,
        "latitude": lat,
        "longitude": lon,
        "speed": speed_mps
    }

    future = producer.send(TOPIC, key=key, value=value)


# Simulation Related Functions
def distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi = math.radians((lat1+lat2)/2.0)
    dx = math.radians(lon2-lon1) * math.cos(phi)
    dy = math.radians(lat2-lat1)
    return R * math.sqrt(dx**2 + dy**2)

# It returns polystops which is a list of coordinates of stops in the routes
def build_route_and_cumdist(stops: List[dict]):
    poly_stops = [(s["location"]["lat"], s["location"]["lon"]) for s in stops]
    cum_dist = [0.0]
    for i in range(len(poly_stops)-1):
        cum_dist.append(cum_dist[-1] + distance(*poly_stops[i], *poly_stops[i+1]))
    return poly_stops, cum_dist

# Calculates Co-ordinates given distance covered
def get_poly_with_dist(poly, cum, s_m) -> Tuple[float, float]:
    
    if s_m <= 0: return poly[0]
    if s_m >= cum[-1]: return poly[-1]

    # binary search to find between which stops the current distance falls
    lo, hi = 0, len(cum)-1
    while lo < hi-1:
        mid = (lo + hi)//2
        if s_m < cum[mid]: hi = mid
        else: lo = mid
    i = lo

    seg_len = cum[i+1] - cum[i]
    r = 0.0 if seg_len == 0 else (s_m - cum[i]) / seg_len
    lat = poly[i][0] + r * (poly[i+1][0] - poly[i][0]) # line formula: finding a point on line give another point on the line and distance from it.
    lon = poly[i][1] + r * (poly[i+1][1] - poly[i][1]) # line formula: finding a point on line give another point on the line and distance from it.
    return lat, lon

# Creates trips (with departure time and route)
def spawn_departures(route: dict, sim_start: datetime, sim_end: datetime):
    """Yield tuples: (route_id, direction, start_time, poly, cum, total_len)"""
    headway_min = route["headway_peak_min"] if USE_PEAK else route["headway_offpeak_min"]
    headway_sec = headway_min * 60

    def make(direction):
        stops = route["stops"] if direction == 0 else list(reversed(route["stops"]))
        poly, cum = build_route_and_cumdist(stops)
        return poly, cum, cum[-1]

    for direction in (0, 1):
        poly, cum, total = make(direction)
        t = sim_start
        while t <= sim_end:
            yield (route["route_id"], direction, t, poly, cum, total) #(Route_id, direction, start_time, dist_arry, cum_dist)
            t += timedelta(seconds=headway_sec)

def create_bus_id(route_id, direction):
    seq[(route_id, direction)] += 1
    return f"{route_id}-D{direction}-#{seq[(route_id, direction)]}"
# simulation starts.
def simulate_bus_gps():
    with open(ROUTES, "r") as f:
        routes = json.load(f)

    sim_end = SIM_START + timedelta(minutes=SIM_MINUTES)

    # Create all planned one-way trips
    trips = []
    for r in routes:
        trips.extend(spawn_departures(r, SIM_START, sim_end))

    # Each bus in the trip gets has own vehicle_id
    trips.sort(key=lambda x: x[2])  # order by start_time
    vehicles = [{
        "route_id": route_id,
        "direction": direction,
        "start_time": start_time,
        "poly": poly,
        "cum": cum,
        "len": total_len,
        "s": 0.0,
        "active": False,  # becomes true when start_time comes
        "vid": create_bus_id(route_id, direction)
    } for i, (route_id, direction, start_time, poly, cum, total_len) in enumerate(trips)]

    create_topics()
    producer = get_producer()

    print("\nStarting Simulation")
    sample_gps_events = []
    current = SIM_START
    while current <= sim_end:
        # Starting new vehicles
        for v in vehicles:
            if not v["active"] and v["start_time"] <= current:
                v["active"] = True
                v["s"] = 0.0

        # moving buses and emit
        for v in vehicles:
            if not v["active"]: 
                continue
            if v["s"] >= v["len"]:
                continue  # destination reached

            # if random.random() < 0.5:
            #     factor = random.uniform(0.90, 1.20)
            #     speed = speed * factor

            # speed
            speed = max(MIN_SPEED_MPS, BASE_SPEED_MPS * max(0.0, random.gauss(1.0, SPEED_NOISE_SIGMA)))
            v["s"] = min(v["len"], v["s"] + speed * DT_SEC)

            lat, lon = get_poly_with_dist(v["poly"], v["cum"], v["s"])
            
            # write_to_kafka(producer, ts_iso, route_id, vehicle_id, direction, lat, lon, speed_mps):
            ts = current.isoformat()
            r_id = v["route_id"]
            v_id = v["vid"]
            direc = v["direction"]
            lat_ = round(lat, 6)
            lon_ = round(lon, 6)
            speed_ = round(speed, 2)
            write_to_kafka(producer, ts, r_id, v_id, direc, lat_, lon_, speed_)

            if len(sample_gps_events) < EMIT_SAMPLES:
                sample_gps_events.append({
                    "timestamp": ts,
                    "route_id": r_id,
                    "vehicle_id": v_id,
                    "direction": direc,
                    "lat": lat_,
                    "lon": lon_,
                    "speed_mps": speed_
                })
            

        current += timedelta(seconds=DT_SEC)
        

    producer.flush()
    producer.close()
    print(f"\nSimulation Completed and ingested to Kafka")
    return sample_gps_events

if __name__ == "__main__":
    simulate_bus_gps()