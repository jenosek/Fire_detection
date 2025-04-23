'''
Send via POST to
coap://YOUR_THINGSBOARD_HOST/api/v1/YOUR_DEVICE_ACCESS_TOKEN/telemetry

Content-Format: application/json
'''

# gen JSON for init message
# Radio_values = ["NB-IoT", CELL_ID, Tracking Area Code, Band, EARFCN]
# GPS = [latitude, longitude]
# DEV_ID = int
# FW_VER = string
# MAN = string
def gen_json_init(radio_values, gps, DEV_ID, FW_VER, MAN):
    json_payload = f"""{{
    "deviceId": {DEV_ID},
    "firmwareVersion": "{FW_VER}",
    "manufacturer": "{MAN}",
    "technology": "{radio_values[0]}",
    "cellId": {radio_values[1]},
    "TAC": {radio_values[2]},
    "band": {radio_values[3]},
    "EARFCN": {radio_values[4]},
    "latitude": {GPS[0]},
    "longitude": {GPS[1]}
    }}"""

    # remove whitespace and stuff
    return json_payload.strip().replace(' ','').replace('\n','').replace('\r','')

# gen JSON for data message
# ALARM = bool
# RSRP = int
# SINR = int
# TEMP = []
# HUM = []
def gen_json_data(ALARM, RSRP, SINR, TEMP, HUM):
    json_payload = f"""{{
    "Alarm": {int(ALARM)},
    "RSRP": {RSRP},
    "SINR": {SINR},
    "length": {len(TEMP)},
    "temperature": {TEMP},
    "humidity": {HUM}
    }}"""

    # remove whitespace and stuff
    return json_payload.strip().replace(' ','').replace('\n','').replace('\r','')