# Proposal: measure what Heilbronn is about to pay for

Written 29 Oct 2026 for the pitch and the "pitch it to city hall" follow-up. Builds on `research/complaints.md` (what people care about), `research/data.md` (what data exists) and the city's own noise documents in `resources/`. Every number below has a source in section 7.

## 1. What the city's reports say

Heilbronn's noise mapping 2022 (Stufe IV, report 103-101/16-B) is a **calculation**, not a measurement: road, rail and industry noise modelled onto every façade. Its results for road traffic:

| | Residents |
|---|---|
| Above 55 dB(A) LDEN (day-evening-night) | 40,100 of about 130,000, roughly 31 % |
| Above 65 dB(A) LDEN, the health-critical line the city itself uses | 16,100 |
| Above 55 dB(A) LNight | 16,300 |
| Dwellings above 55 dB(A) LDEN | 19,200 |
| School buildings above 55 dB(A) LDEN | 50 |

Health effects the report estimates: 12,450 people highly annoyed, 3,202 highly sleep-disturbed, 1,817 cases of ischaemic heart disease. Stadtbahn and industry: no action needed. The problem is road traffic.

On 7 Oct 2024 the council adopted the Lärmaktionsplan Stufe IV (DS 208/2024). Its measures until 2028:

| Measure | Where | Expected effect | Cost |
|---|---|---|---|
| Low-noise asphalt | Südstraße, Wilhelm-Leuschner-Str., Karlsruher Str./Weststr., Neckarsulmer Str., Wilhelmstraße, Mannheimer/Weinsberger Str., Paulinenstraße | about 3 dB(A) | 2,525,000 € |
| Tempo 30 | Frankenbacher Str., Heidelberger Str., Theodor-Heuss-Str. | about 2.5 dB(A) | signs only |
| Noise-protection windows | 24 streets, subsidy now from 65 dB LDEN / 55 dB LNight | healthier sleep | 30,000 € per year |
| Speed enforcement, more e-vehicles, quiet areas | hotspots, Betriebsamt fleet, Neckar banks and BUGA parks | supporting | in existing budgets |

**How the city plans to check whether it worked** (plan section 5.2): a comparison with 2019 is impossible because the calculation method changed. The effect of the 2.5 million euros will be evaluated in the next mapping round, 2029, again by calculation. Nobody will measure before or after the works.

## 2. What people care about

- **Noise is the complaint nobody can file.** 67 % of Germans are annoyed by road traffic noise at home, 58 % by neighbours (UBA 2024). Heilbronn's Mängelmelder took about 9,000 reports in three years and 13,800 by Nov 2025, in 13 categories: trash, roads, lighting. No noise, no heat, no air. People report what the form offers.
- **The official channel is narrow and short.** The noise action plan consultation was open for two windows of one month each and only accepted input "on road traffic". 23 people answered in 2023, 13 in 2024. The window-subsidy scheme of 2015/16 received exactly one application.
- **What citizens actually named** in those 36 answers: Allee, Frankenbacher, Haller, Heidelberger, Ludwigsburger, Lutz-, Sontheimer and Stuttgarter Straße, plus "Poser" and commercial noise. The city's answer: Poser and Gewerbelärm fall outside the EU directive. So they are not mapped, not counted, not measured.
- **Speed is often not the lever.** The Ordnungsamt's enforcement trailer logged 841,621 vehicles on Mannheimer Straße in 2022: 0.31 % too fast. On Südstraße it was 0.58 %. The noise there is volume, surface and single loud vehicles, which only a microphone can tell apart.
- **Heat and air are the same story.** Two thirds of Germans say heat periods burden their health; 26 % say their home is not protected from summer heat, 24 % that their local air is not clean. Heilbronn is 54 % sealed, the worst heat score in Baden-Württemberg. The Klimaanpassungskonzept (June 2025) names the priority zone Hauptbahnhof–Allee–Mannheimer Str.–Rollwagstraße and plans to unseal Marktplatz, Hafenmarkt and Kiliansplatz. Again without a before-and-after measurement plan.

## 3. The gap in one sentence

Heilbronn knows where it is loud on paper, is spending 2.5 million euros on it, and has no way to hear whether it worked or to hear the places and sources its paper does not cover.

## 4. What to do about it

Five actions, in order of value for money. Actions 1 and 2 use hardware and software that exist today in this repo.

### 4.1 Measure every street in the action plan before and after the works

One NoiseNode (senseBox MCU-S2 plus a DFRobot sound level meter, roughly 100 to 150 € in parts, 3D-printed case) at the facade of each of the seven asphalt streets and three Tempo-30 streets. Four weeks before the works, four weeks after, same spot, same height. It logs LAeq per minute, Lmax per minute and the number of loud events per minute, no audio.

- Cost: about 1,500 € for ten nodes, under 0.1 % of the asphalt budget.
- Result: the city can state "Südstraße: 3.1 dB(A) quieter at night" in 2027 instead of a recalculation in 2029. It also catches the opposite, a surface that does not deliver, while the contractor's warranty still runs.
- Owner: Planungs- und Baurechtsamt, which already runs the "Regelmäßige Abfrage" on implementation. Data goes to openSenseMap and the Green City Dashboard, as the senseBox:home stations already do.

### 4.2 Open a permanent channel for conditions, not incidents

Add "Zu laut", "Zu heiß", "Schlechte Luft" and "Kein Schatten" as report types next to the Mängelmelder. The Mängelmelder takes an incident a worker fixes in ten days. These are conditions a place has, and the city only acts on them once they are measured. Sag's Heilbronn already does the full loop:

1. a person reports how a place feels, location from GPS, three taps;
2. the report is checked against data that exists: the 2022 noise map, senseBox:home temperature and PM, the last senseBox:bike pass, the tree register for shade;
3. where no data exists, the cluster is ranked ("Platz 1 von 8 Stellen ohne Sensor") and the next sensor goes there;
4. the person gets an answer card. People whose first report gets a response are 57 % more likely to report again.

The consultation got 36 answers in two years. A channel that is open all year, on a phone, with an answer, is how the city learns what the next action plan must contain.

### 4.3 Measure the sources the directive leaves out

The streets citizens named and the city could not act on get nodes next. Night-time Lmax and event counts are exactly the evidence for Poser and commercial noise that the Ordnungsamt lacks today. The city already measures speed with trailers at hotspots. Measuring sound at the same spots costs a fraction and answers a different question: not "how fast" but "how loud, how often, when".

### 4.4 Run heat and air through the same loop

Before unsealing Marktplatz, Hafenmarkt and Kiliansplatz, put a senseBox:home on each for a summer. The Innenstadt box already shows what the gap looks like: 112 days over 30 °C at the sensor since March against 7 in Neckargartach. The unsealing budget is far larger than the asphalt budget. It deserves a before-and-after number as well.

### 4.5 Feed the 2029 mapping with measured data

Ten to twenty fixed nodes over three years give the 2029 round calibration points. The 2024 plan admits its own numbers cannot be compared with 2019. Measured series make the next comparison real, and they let the city defend its quiet areas (Stadtgarten, Pfühlpark, Neckar banks) with data instead of designation alone.

## 5. Cost and timeline

| | Nodes | Parts | When |
|---|---|---|---|
| 4.1 before/after on action-plan streets | 10 | about 1,500 € | before the first asphalt works, 2027 |
| 4.3 citizen-named streets and night events | 8 | about 1,200 € | 2027 |
| 4.4 three squares, heat | 3 senseBox:home | about 1,000 € | summer 2027 |
| 4.2 report channel | software, exists | hosting on one Raspberry Pi | now |

Total hardware under 4,000 €. The expensive part is not money but an owner: one person in the Planungs- und Baurechtsamt who places the nodes and reads the dashboard once a month.

## 6. What exists today

- The app at https://greencity.parsalotfi.com/: report, cluster, check against sensor data, answer card, map layers for the 2022 noise map, bike PM and trees.
- One NoiseNode live on openSenseMap since 28 Oct 2026, streaming LAeq, Lmax and event counts per minute into the same map.
- The case, the firmware, the backend and this analysis in one repository, ready to hand over.

## 7. Caveats

- Low-cost sound level meters are not class-1 instruments. Absolute values carry a few dB of uncertainty. Before-and-after at the same spot with the same node is a relative measurement, which is what action 4.1 needs. A 3 dB change is well above that noise floor over four weeks of minute data.
- Nodes measure at one facade. The map models all facades. The two complement each other, they do not replace each other.
- No audio is recorded or transmitted. Only levels and counts. That keeps it outside privacy objections that have stopped other cities.
- Mängelmelder category counts and the UBA 2024 survey figures come from press and conference summaries, see `research/complaints.md`. The noise map, action plan, costs and enforcement figures are from the city's own documents.

## 8. Sources

- Lärmkartierung 2022, Stufe IV, Bericht 103-101/16-B, schall.tech (Fend), draft 5 Jan 2023: `resources/103-101-16-B_Kartierungsergebnisse.pdf`, maps `Anlage_1.1` to `3.2`.
- DS 223/2023, Betroffenheitsanalyse, 12 Jun 2023: hotspots, enforcement figures, window programme, consultation rules. heilbronn.de, laermaktionsplan_stufe_IV/Betroffenheitsanalyse_2023.
- Lärmaktionsplan Stufe IV, Anlage 1 to DS 208/2024, in force 7 Oct 2024: measures, costs, participation (23 + 13), evaluation by calculation in 2029. heilbronn.de, laermaktionsplan_stufe_IV/Drucksache_Laermaktionsplan_Stufe_IV/Anlage_1_Laermaktionsplan.pdf.
- echo24, 24 Apr 2024: Tempo 30 draft, streets excluded at the transit operator's request.
- UBA Umweltbewusstsein 2024 and UBA Lärmbelästigung page; DUH Hitze-Check 2024; Klimaanpassungskonzept Heilbronn via echo24 12 Jun 2025; Mängelmelder figures via Stadtzeitung 27 Nov 2024 and Stimme 21 Nov 2025; Sjoberg, Mellon, Peixoto 2017, Public Administration Review 77(3). All as listed in `research/complaints.md`.
