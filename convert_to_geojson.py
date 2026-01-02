import re
import json
import sys

INPUT_FILE = "ogimet_data.txt"
OUTPUT_FILE = "weather_stations.geojson"

def dms_to_decimal(dms_str):
    """
    Converts DMS string (e.g., "34-02-59N", "074-24-00E") to decimal degrees.
    """
    match = re.match(r'(\d+)-(\d+)-(\d+)([NSEW])', dms_str)
    if not match:
        raise ValueError(f"Invalid DMS string: {dms_str}")
    
    degrees, minutes, seconds, direction = match.groups()
    decimal = float(degrees) + float(minutes)/60 + float(seconds)/3600
    
    if direction in ['S', 'W']:
        decimal *= -1
        
    return round(decimal, 6)

def decode_visibility(vv_str):
    """Decodes VV code to km (WMO Table 4377)."""
    try:
        vv = int(vv_str)
        if vv <= 50:
            return vv * 0.1
        elif 56 <= vv <= 80:
            return float(vv - 50)
        elif 81 <= vv <= 88:
            return 30 + (vv - 80) * 5.0
        elif vv == 89:
            return 75.0 # >70km
        
        # WMO Code Table 4377 (90-99)
        elif vv == 90: return 0.05 # <0.05
        elif vv == 91: return 0.05
        elif vv == 92: return 0.2
        elif vv == 93: return 0.5
        elif vv == 94: return 1.0
        elif vv == 95: return 2.0
        elif vv == 96: return 4.0
        elif vv == 97: return 10.0
        elif vv == 98: return 20.0
        elif vv == 99: return 50.0 # >50
        
        return None
    except ValueError:
        return None

def decode_synop(raw_data, station_id):
    """
    Decodes comprehensive variables from SYNOP string (FM-12).
    """
    data = {}
    
    # Clean and tokenize
    content = raw_data.replace('=', ' ').replace('/', 'X')
    tokens = content.split()
    
    # Locate Station ID to start Section 1
    try:
        start_idx = tokens.index(station_id)
        section1_tokens = tokens[start_idx+1:]
    except ValueError:
        # Fallback
        section1_tokens = tokens
    
    # --- SECTION 1 PARSING ---
    # Fixed groups after Station ID:
    # 1. irixhVV (Precip indicator, Weather indicator, Cloud base, Visibility)
    # 2. Nddff (Cloud cover, Wind Direction, Wind Speed)
    
    current_idx = 0
    
    # Group 1: irixhVV
    if current_idx < len(section1_tokens):
        grp = section1_tokens[current_idx]
        if len(grp) == 5:
            # ix (index 1): Weather indicator
            # 1 = Manned, weather included
            # 2 = Manned, no significant weather (omit group 7)
            # 3 = Manned, no significant weather (omit group 7)
            # 4 = Automated...
            ix = grp[1]
            if ix == '2' or ix == '3':
                data['present_weather_code'] = "no_sig" # Indicates fair/no significant weather
                data['weather_observed'] = False # As per user request concept
            
            # h (index 2): Cloud base height
            h_char = grp[2]
            if h_char.isdigit():
                 data['cloud_base_height_code'] = int(h_char)
            elif h_char == '9': # >2500m or no clouds
                 data['cloud_base_height_code'] = 9
            elif h_char == 'X':
                 data['cloud_base_height_code'] = None

            # VV (index 3-4): Visibility
            data['visibility_km'] = decode_visibility(grp[3:5])
        current_idx += 1
        
    # Group 2: Nddff
    if current_idx < len(section1_tokens):
        grp = section1_tokens[current_idx]
        if len(grp) == 5:
            # Cloud Cover (N)
            n_char = grp[0]
            if n_char.isdigit():
                data['cloud_cover_octas'] = int(n_char) if int(n_char) <= 8 else 9
            elif n_char == 'X':
                data['cloud_cover_octas'] = None
                
            # Wind (ddff)
            try:
                dd = int(grp[1:3])
                ff = int(grp[3:5])
                
                if dd == 0 and ff == 0:
                     data['wind_direction_deg'] = 0
                elif dd == 99:
                     data['wind_direction_deg'] = "Variable"
                else:
                     data['wind_direction_deg'] = dd * 10
                data['wind_speed_kt'] = ff
            except ValueError:
                pass
        current_idx += 1
        
    # Variable Groups (Section 1)
    in_section_3 = False
    
    for i in range(current_idx, len(section1_tokens)):
        token = section1_tokens[i]
        
        if token == '333':
            in_section_3 = True
            continue
            
        if len(token) != 5:
            continue
            
        group_id = token[0]
        
        # --- SECTION 1 GROUPS ---
        if not in_section_3:
            # 1snTTT: Temperature
            if group_id == '1':
                try:
                    sign = -1 if token[1] == '1' else 1
                    val = int(token[2:5])
                    if val != 999:
                        data['temperature_c'] = val * 0.1 * sign
                except ValueError: pass
                
            # 2snTdTdTd: Dew Point
            elif group_id == '2':
                try:
                    sign = -1 if token[1] == '1' else 1
                    val = int(token[2:5])
                    if val != 999:
                        data['dew_point_c'] = val * 0.1 * sign
                except ValueError: pass
            
            # 3PPPP / 4PPPP: Pressure
            elif group_id == '4':
                try:
                    if token[1] != 'X':
                        val = int(token[1:5])
                        pressure = val * 0.1
                        if pressure < 100: pressure += 1000
                        data['pressure_hpa'] = round(pressure, 1)
                except ValueError: pass

            elif group_id == '3':
                try:
                    if token[1] != 'X':
                         val = int(token[1:5])
                         pressure = val * 0.1
                         if pressure < 100: pressure += 1000
                         data['station_pressure_hpa'] = round(pressure, 1)
                except ValueError: pass
                
            # 5appp: Pressure Tendency
            elif group_id == '5':
                try:
                    # a: characteristic (0-8)
                    char_a = token[1]
                    # ppp: change in 0.1 hPa
                    if char_a != 'X' and token[2] != 'X':
                        change = int(token[2:5]) * 0.1
                        data['pressure_tendency_characteristic'] = int(char_a)
                        
                        # Apply sign based on characteristic (WMO Table 0200)
                        # 0-3: Higher/Same (Positive)
                        # 4: Same (Zero) - Change likely 000
                        # 5-8: Lower (Negative)
                        a_val = int(char_a)
                        if 5 <= a_val <= 8:
                            change *= -1
                        
                        data['pressure_change_3h'] = round(change, 1)
                        data['pressure_tendency_3h_hpa'] = round(change, 1) # Alias for clarity
                except ValueError: pass
            
            # 6RRRt: Precipitation
            elif group_id == '6':
                try:
                     rrr_code = int(token[1:4])
                     precip = 0.0
                     if rrr_code < 990:
                         precip = float(rrr_code)
                     elif rrr_code == 990: precip = 0.05 # Trace
                     data['precip_amount_mm'] = precip
                except ValueError: pass
                
            # 7wwW1W2: Weather
            elif group_id == '7':
                try:
                    ww = token[1:3]
                    data['present_weather_code'] = ww
                except ValueError: pass
                
            # 8NhCLCMCH: Clouds
            elif group_id == '8':
                try:
                    nh = token[1]
                    cl = token[2]
                    cm = token[3]
                    ch = token[4]
                    
                    if nh.isdigit(): data['low_cloud_amount_octas'] = int(nh)
                    if cl.isdigit(): data['low_cloud_type_code'] = int(cl)
                    if cm.isdigit(): data['mid_cloud_type_code'] = int(cm)
                    if ch.isdigit(): data['high_cloud_type_code'] = int(ch)
                except ValueError: pass
        
        # --- SECTION 3 GROUPS ---
        else:
            # 1snTxTxTx / 2snTnTnTn
            if group_id == '1':
                try:
                    sign = -1 if token[1] == '1' else 1
                    val = int(token[2:5])
                    if val != 999: data['max_temp_c'] = val * 0.1 * sign
                except ValueError: pass
                
            elif group_id == '2':
                try:
                    sign = -1 if token[1] == '1' else 1
                    val = int(token[2:5])
                    if val != 999: data['min_temp_c'] = val * 0.1 * sign
                except ValueError: pass
            
            # 5appp: Pressure Tendency logic (India/Region specific usage in Section 3)
            # User example: 58041 -> a=8, ppp=041
            elif group_id == '5':
                try:
                    char_a = token[1]
                    if char_a != 'X' and token[2] != 'X':
                         change = int(token[2:5]) * 0.1
                         data['pressure_tendency_characteristic'] = int(char_a)
                         
                         a_val = int(char_a)
                         # Sign logic: 5-8 is negative
                         if 5 <= a_val <= 8:
                             change *= -1
                         
                         data['pressure_change_3h'] = round(change, 1)
                         data['pressure_tendency_3h_hpa'] = round(change, 1)
                except ValueError: pass

    # Round floats
    for k, v in data.items():
        if isinstance(v, float):
            data[k] = round(v, 1)
            
    return data

def parse_stations_from_text(content):
    """
    Parses station data directly from text content string.
    """
    stations = []
        
    # Split by station header lines
    # Pattern to find station headers
    header_pattern = r'#\s+SYNOPS from (\d+), (.+?) \((.+?)\) \| (\d{2,3}-\d{2}-\d{2}[NS]) \| (\d{3}-\d{2}-\d{2}[EW]) \| (\d+) m'
    
    # We will iterate through match objects to find positions
    matches = list(re.finditer(header_pattern, content))
    
    for i, match in enumerate(matches):
        station_id = match.group(1)
        name = match.group(2)
        country = match.group(3)
        lat_str = match.group(4)
        lon_str = match.group(5)
        elevation = int(match.group(6))
        
        try:
            lat = dms_to_decimal(lat_str)
            lon = dms_to_decimal(lon_str)
        except ValueError as e:
            # print(f"Skipping station {name} ({station_id}): {e}")
            continue
            
        # Extract raw data associated with this station
        # It's the text between this match end and next match start (or EOF)
        start_idx = match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(content)
        
        # Get the chunk of text
        raw_chunk = content[start_idx:end_idx].strip()
        
        # Let's clean up the raw chunk. 
        # Usually it starts with a line of ####
        lines = raw_chunk.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            cleaned_lines.append(line)
        
        raw_data = "\n".join(cleaned_lines)
        
        # Decode variables
        meteo_data = decode_synop(raw_data, station_id)
        
        props = {
            "station_id": station_id,
            "name": name,
            "country": country,
            "elevation_m": elevation,
            "raw_synop": raw_data
        }
        # Merge decoded data
        props.update(meteo_data)
        
        stations.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat] # GeoJSON is [lon, lat]
            },
            "properties": props
        })
        
    return stations

def parse_stations(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return parse_stations_from_text(content)

def main():
    try:
        print(f"Reading from {INPUT_FILE}...")
        stations = parse_stations(INPUT_FILE)
        
        geojson = {
            "type": "FeatureCollection",
            "features": stations
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
            
        print("-" * 30)
        print(f"Success! Converted {len(stations)} stations to GeoJSON.")
        print(f"Output saved to: {OUTPUT_FILE}")
        print("-" * 30)
        
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Please run get_ogimet_data.py first.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
