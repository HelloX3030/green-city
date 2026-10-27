# The app

People report what bothers them. We check it against sensor data. Where the data is silent, a sensor goes there.

## Loop

1. **Report** – tap *Report*, pick the issue, send with location.
2. **Cluster** – reports close in space and time form a cluster.
3. **Check** – the cluster is compared with historical sensor data nearby. Status: `confirmed`, `unconfirmed`, `no data`.
4. **Measure** – a `no data` cluster is where the next sensor goes. It streams live into the same map.

## Reports

See `Reports.md` for the list. Each report has: issue type(s), location (GPS or picked on map), timestamp, optional text.

Reports don't expire. Their weight decays over time: old ones fade from the map but stay in the data.

Historical data per issue:

| Issue       | Data                                   |
|-------------|----------------------------------------|
| Temperature | senseBox:home, heat walks              |
| Humidity    | senseBox:home                          |
| Air quality | senseBox PM, LUBW station              |
| Noise       | only modelled noise maps, no sensors → the gap |

## Frontend

One mobile page behind a QR code. No login.

- **Map** of Heilbronn: clusters (size = weight, color = status), live sensor pins.
- **Cluster popup**: count, issue types, status, one-line reason.
- **Sensor popup**: live values.
- **Report sheet**: pick issues, confirm location, optional text, send. Three taps.
- **Voice** (later): speak the report, we structure it.

## Backend

One service, one database.

- `POST /reports` – create
- `GET /reports` – weighted, for the map
- `GET /clusters` – with status and reason
- `GET /sensors` – live nodes, latest values

Validation runs on each new report for its cluster, plus a full pass on a timer. Compares nearby historical readings with the city-wide median for the same hour.

Live values come from our own nodes and the existing senseBox network.

## Not now

Volunteer management, accounts, moderation, notifications. One real node on stage instead.
