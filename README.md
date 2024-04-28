# courtavail-api
A very niche API to scrape available tennis court times from the Prospect Park Tennis Center. 

Basically does what the name says. The tenniscourts_v1.py script makes a request to the Prospect Park Tennis Center's website to get the bookings for a given day, and then works backwards to calculate how many bookings exist at a given time. Some of the stuff around time cleaning is a little messy (handling for half-hour availabilities, etc).

The API is a super simple FastAPI, you submit the request in the format /date/[YYYY-MM-DD], and it returns a simple list with any available times for that day. It won't include times in the past if the target date is today.

It autodeploys to fly.io using Github actions. 
