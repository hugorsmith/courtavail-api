import requests
import json
from datetime import datetime, date, timedelta
import pytz

# Scraping configuration

HEADERS = {
        'authority': 'prospectpark.aptussoft.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://prospectpark.aptussoft.com',
        'referer': 'https://prospectpark.aptussoft.com/Member/Aptus/Calender',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Brave";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

BASE_URL = "https://prospectpark.aptussoft.com/Member/"

# Utility functions
def format_date_for_server(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")

def convert_to_iso8601(time_str, date_str):
    datetime_obj = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M")
    return datetime_obj.isoformat()

def convert_iso8601_to_12h(iso8601_str):
    dt = datetime.fromisoformat(iso8601_str)
    return dt.strftime("%I:%M %p")

def convert_12h_to_iso8601(time_str):
    dt = datetime.strptime(time_str, "%I:%M %p")
    return dt.isoformat()

def get_today_date():
    return date.today().strftime("%Y-%m-%d")

# Get current time in EST
EST = pytz.timezone('US/Eastern')

def get_current_time_12h_est():
    datetime_est = datetime.now(EST)
    return datetime_est.strftime("%I:%M %p")

def clean_court_times(court_available_times, target_date):
    # Get the current date and time in EST
    
    current_time = datetime.now(EST)
    next_start = current_time.replace(second=0, microsecond=0, minute=0, hour=current_time.hour + 1)

    # Prepare to collect cleaned times
    cleaned_times = []

    # Current date to attach to time entries
    current_date = current_time.date()
    target_date_dt = datetime.strptime(str(current_date), "%Y-%m-%d")

    for time in court_available_times:
        # Parse the time with the target date
        time_dt = datetime.strptime(f"{target_date} {time}", "%Y-%m-%d %I:%M %p")
        # Localize the datetime object
        time_dt = EST.localize(time_dt)

        # 
        # print("Checking time:", time, "->", time_dt)

        # Keep only times that are later than the next hour start
        if time_dt >= next_start:
            cleaned_times.append(time)

    return cleaned_times

# Main functions
def create_session():
    session = requests.Session()
    session.get(BASE_URL, headers=HEADERS)
    return session.cookies.get_dict()

def get_operating_hours(cookies):
    data = {
        'locationid': 'Brooklyn',
    }

    response = requests.post(
        f'{BASE_URL}Aptus/CourtBooking_ResourceListByLookupId',
        cookies=cookies,
        headers=HEADERS,
        data=data,
    )

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return None

def fetch_court_bookings(date, cookies):
    data = {
        'acctno': '14900',
        'locationid': 'Brooklyn',
        'resourcetype': 'Clay',
        'start': date,
        'end': date,
        'CalledFrom': 'WEB',
    }

    response = requests.post(
        f'{BASE_URL}Aptus/CourtBooking_Get',
        cookies=cookies,
        headers=HEADERS,
        data=data,
    )

    if response.status_code == 200:

        return json.loads(json.loads(response.text)['CourtBooking_GetResult'])
    else:
        return None

def get_court_availability(date):
    cookies = create_session()
    formatted_date = format_date_for_server(date)
    operating_hours = get_operating_hours(cookies)

    if not operating_hours:
        return "Failed to fetch operating hours"

    # Extract court open and close times
    court_open_time = operating_hours['ItemStime']
    court_close_time = operating_hours['ItemEtime']

    # Generate all possible times in 24-hour format
    all_times = ['{:02d}:{:02d}'.format(hour, minute) for hour in range(24) for minute in [0, 30]]

    # Find indices for open and close times
    try:
        index_open_time = all_times.index(court_open_time)
        index_close_time = all_times.index(court_close_time)
    except ValueError:
        return "Invalid operating hours received"

    # List of available times in the operating hours
    unformatted_available_times = all_times[index_open_time:index_close_time]

    # Convert times to ISO 8601 format
    available_times = [convert_to_iso8601(time, date) for time in unformatted_available_times]

    # Initialize booking counts
    booking_count = {time: 0 for time in available_times}

    # Fetch bookings
    fetched_bookings = fetch_court_bookings(formatted_date, cookies)
    if not fetched_bookings or len(fetched_bookings) < 2:
        return "Failed to fetch booking data"

    # Process each booking
    target_bookings = fetched_bookings[1]  # Assuming the bookings are in the second item

    for booking in target_bookings:
        start = booking['start']
        end = booking['end']

        fmt_start = datetime.fromisoformat(start)
        fmt_end = datetime.fromisoformat(end)

        length = fmt_end - fmt_start
        length_hrs = length.total_seconds() / 3600

        try:
            start_idx = available_times.index(start)
        except ValueError:
            continue  # Skip booking if start time is not in available times

        # Count bookings for each time slot
        booking_count[available_times[start_idx]] += 1

        # Increment booking count for each hour of booking duration
        while length_hrs > 0.5:
            start_idx += 1
            if start_idx >= len(available_times):
                break
            booking_count[available_times[start_idx]] += 1
            length_hrs -= 0.5

    # Number of clay courts available
    num_clay_courts = 9

    # Determine available time slots
    court_available_times = []

    for time in booking_count:
        if not time.endswith("22:30:00"):
            next_time = available_times[available_times.index(time) + 1]
            if booking_count[time] < num_clay_courts and booking_count[next_time] < num_clay_courts:
                print_time = convert_iso8601_to_12h(time)
                court_available_times.append(print_time)
    

    
    date_raw =  EST.localize(datetime.strptime(date, "%Y-%m-%d"))
    today = datetime.now(EST)

    if date_raw <= today:
        print("Cleaning times")
        # print(court_available_times)
        court_available_times = clean_court_times(court_available_times, date)


    # Get rid of 30 minute time slots
    court_available_times = [time for time in court_available_times if time.split(':')[1][:2] != "30"]
    
    
    return court_available_times


x = get_court_availability("2024-04-30")
print(x)