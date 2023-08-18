import re

def short_to_long_year(short_year: int, current_year: int) -> int:
    current_modifier = round(current_year, -2)
    past_modifier = current_modifier - 100
    future_modifier = current_modifier + 100
    current_full_year = current_modifier + short_year
    past_full_year = past_modifier + short_year
    future_full_year = future_modifier + short_year
    if abs(current_year - current_full_year) <= abs(current_year - past_full_year):
        if abs(current_year - current_full_year) < abs(current_year - future_full_year):
            return current_full_year
        else:
            return future_full_year
    else:
        if abs(current_year - past_full_year) < abs(current_year - future_full_year):
            return past_full_year
        else:
            return future_full_year

def parse_timezone(tz_text: str) -> int:
    tz_match = re.search("([+-])(\d?\d)(?::([0-5]\d))?", tz_text)
    if not tz_match:
        raise ValueError
    tz_sign = 1 if tz_match[1] == "+" else -1
    tz_hour = int(tz_match[2])
    tz_minute = int(tz_match[3]) if tz_match[3] else 0
    tz_offset_seconds = tz_sign * 60 * (tz_hour * 60 + tz_minute)
    return tz_offset_seconds