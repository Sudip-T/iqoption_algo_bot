from datetime import datetime, timedelta


def get_timestamps(start_str: str = None, end_str: str = None) -> tuple:
    try:
        # If no end date provided, use current time
        if end_str is None:
            end_dt = datetime.now()
        else:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")

        if start_str is None:
            start_dt = end_dt - timedelta(hours=24)
        else:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")

        return int(start_dt.timestamp()), int(end_dt.timestamp())
    except Exception as e:
        print(str(e))
        print('Plase make sure date is within valid range')
        return None, None


def get_expiration(timestamp:int, expiry:int=1):
    # Convert timestamp from milliseconds to seconds
    min_time_needed = 31
    timestamp = timestamp / 1000

    # Create datetime object from timestamp
    now_date = datetime.fromtimestamp(timestamp)

    # Round down to nearest minute (remove seconds and microseconds)
    now_date_hm = now_date.replace(second=0, microsecond=0)

    # Calculate expiration based on conditions
    if expiry == 1:
        if (now_date_hm + timedelta(minutes=1)).timestamp() - timestamp >= min_time_needed:
            expiration = now_date_hm + timedelta(minutes=1)
        else:
            expiration = now_date_hm + timedelta(minutes=2)
    else:
        time_until_expiry = (now_date_hm + timedelta(minutes=1)).timestamp() - timestamp

        expiration = now_date_hm + timedelta(minutes=expiry)
        
        if time_until_expiry < min_time_needed:
            expiration = now_date_hm + timedelta(minutes=expiry+1)

    return expiration.timestamp()