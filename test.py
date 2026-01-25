def _parse_time_to_seconds(time_str):
    """
    Parses a time string (HH:MM:SS, MM:SS, or SS) into total seconds.
    Returns None if parsing fails.
    """
    if not time_str:
        return 0 # An empty string or None can be interpreted as 0 seconds

    try:
        parts = [int(p) for p in time_str.split(':')]
        if len(parts) == 3:  # HH:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:  # MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:  # SS
            return parts[0]
        else:
            return None # Invalid number of parts
    except ValueError:
        return None # Failed to convert to int
    
if __name__ == '__main__':
    a = ['18:41', '0:15', '1:14:41', '35:20']
    for  i in a:
        print(i, _parse_time_to_seconds(i))