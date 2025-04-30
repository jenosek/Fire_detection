import machine
import radio
import tmplib as TMP
import uselect, sys
import time
import BG77
import gen_json
from PSM import PSM


# CONSTANTS
## MEASURING
I2C_SDA = 14
I2C_CLK = 15
SENSOR_ADDRESS = 56
TEMP_THR = 30
PERIOD = 2000
TOTAL_MEAS_ITER = 5

## WIRELESS
DEV_ID = 24
FW_VER = "1.0.0"
MAN = "VUT Brno"
GPS = [49.2267250, 16.5743461]
AccessT = "2njiwhpsv38zc0i49214"
DevID = "14279d50-1f84-11f0-9037-29f37c847020"
IP_ADDRESS = "62.245.74.185"
PORT = 63404

# ARRAYS
temp = []
hum = []

# VARIABLES
global alarm
global notify_alarm
alarm = False
notify_alarm = False

# RADIO WAKE UP
spoll=uselect.poll()
spoll.register(sys.stdin,uselect.POLLIN)
pon_trig = machine.Pin(9,machine.Pin.OUT)
pon_trig.value(1)
time.sleep(.3)
pon_trig.value(0)
time.sleep(5)

# HANDLERS AND INITS
## I2C Handler (sensor)
i2c_handler = machine.I2C(1, sda=machine.Pin(I2C_SDA), scl=machine.Pin(I2C_CLK), freq=100000)

## Initialize AHT20
sensor = TMP.AHT20(i2c_handler, SENSOR_ADDRESS)

## Initialize radio
module = radio.RADIO()
module.connect_radio()


## Initialize PSM
psm = PSM(module, pon_trig)

## Enable PSM

if psm.enable():
    print("PSM mode enabled successfully")

    psm_status = psm.get_psm_status()
    if psm_status:
        print(f"PSM status: Enabled={psm_status['enabled']}")
        print(f"Network TAU: {psm_status['network_tau']}")
        print(f"Network Active Time: {psm_status['network_active']}")
else:
    print("Failed to enable PSM mode")

# FUNCTIONS
## Read sensor
def irq_meas(_):
    sensor.readSensor()
    temp.append(sensor.temperature)
    hum.append(sensor.humidity)
    global alarm 
    global notify_alarm

    if (sensor.temperature <= TEMP_THR and alarm):
        notify_alarm = True
        alarm = False

    if (sensor.temperature > TEMP_THR and not alarm) :
        alarm = True
        notify_alarm = True
    

## Returns [SINR, RSRP] values as ints
def getSINRandRSRP(module):
    response = module.sendCommand("AT+QCSQ\r\n")
    while "NBIoT" not in response and len(response.split(","))>3:
        time.sleep(1)
        response = module.sendCommand("AT+QCSQ\r\n")
        print(response)
    listResp = response.split(",")
    print(listResp)
    RSRP = int(listResp[2]) #bug???
    SINR = int(int(listResp[3])*0.2-20)
    return SINR, RSRP

## Returns List of strings Radio_values = ["NB-IoT", CELL_ID, Tracking Area Code, Band, EARFCN]
def getStartInfo():
    response = module.sendCommand("AT+QNWINFO\r\n")
    while "NBIoT" not in response:
        time.sleep(1)
        response = module.sendCommand("AT+QNWINFO\r\n")
        print(response)
        
    rsp = module.sendCommand("AT+CEREG?\r\n")
    while "4,5" not in rsp:
        time.sleep(1)
        rsp = module.sendCommand("AT+CEREG?\r\n")
        print(rsp)
    listRSP = rsp.split(",")    
    listResp = response.split("\r")[0].split(",")    
    return ["NBIoT",listRSP[3],listRSP[2],listResp[2], listResp[3]]

        

# Create and send telemetry as JSON 
json_init_payload = gen_json.gen_json_init(getStartInfo(), GPS, DEV_ID, FW_VER, MAN)

success, mysocket = module.socket(BG77.AF_INET, BG77.SOCK_DGRAM, BG77.SOCK_CLIENT, BG77.SOCK_PUSH_BUFFER)
mysocket.connect(IP_ADDRESS, PORT, 0)
if module.isRegistered():   
    mysocket.send(json_init_payload)

## Timer
timer = machine.Timer()
timer.init(mode=machine.Timer.PERIODIC, period=PERIOD, callback=irq_meas)

while(1):
    if (len(temp) == TOTAL_MEAS_ITER or notify_alarm):
        sinr, rsrp = getSINRandRSRP(module)

        sensor_json_payload = gen_json.gen_json_data(alarm, rsrp, sinr, temp, hum)
        '''
        print("Temperature array:", temp)
        print("------")
        print("Humidity array:", hum)
        print("------")
        '''
        if module.isRegistered():   
            mysocket.send(sensor_json_payload, rai=2)
        else:
            print("Not registered")
            module.connect_radio()

        temp.clear()
        hum.clear()
        notify_alarm = False
        
        
    