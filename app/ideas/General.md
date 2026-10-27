# General ideas for the report app:

## Frontend:
### Map with reports in heilbronn. You can select reports and get a summary. You can also see live sensors and click on them for live data.
### There is a report button, you click it and get a list of issues to select. You select at least one issue and send it with your locational data. The report is parsed and added to the dataset. Each report should live for up to like a week or something.
### Thats pretty much it for now.

## Backend:
### Required for having the data central (reports), then feeding it to the frontend (aka the report data is fetched in intervals by the frontend (polling) and the same for the "live" sensor data).
### If we then add validation via historical data and obviously data analysis to find hotspots, that is done centrally, possibly in daily intervals or with each report (idk).
