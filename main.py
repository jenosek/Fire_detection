import machine
import tmplib as TMP
import uselect, sys
import time
import BG77
import gen_json



# CONSTANTS
## MEASURING
I2C_SDA = 14
I2C_CLK = 15
SENSOR_ADDRESS = 56
TEMP_THR = 20
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
alarm = False

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

## UART Handler (Radio)
bg_uart = machine.UART(0, baudrate=115200, tx=machine.Pin(0), rxbuf=256, rx=machine.Pin(1), timeout = 0, timeout_char=1)


## Initialize AHT20
sensor = TMP.AHT20(i2c_handler, SENSOR_ADDRESS)

## Initialize Radio (HW)
bg_uart.write(bytes("AT\r\n","ascii"))
print(bg_uart.read(10))

## Radio Module Class Init
module = BG77.BG77(bg_uart, verbose=True, radio=False)
time.sleep(3)
module.sendCommand("AT+QCFG=\"band\",0x0,0x80084,0x80084,1\r\n")
module.setRadio(1)
module.setAPN("lpwa.vodafone.iot")
module.sendCommand("AT+QCSCON=1\r\n")
time.sleep(3)
module.setRadio(1)
resp = module.sendCommand("AT+QNWINFO\r\n")
while "NBIoT" not in resp:
    time.sleep(3)
    module.sendCommand("AT+COPS=1,2,23003\r\n")
    resp = module.sendCommand("AT+QNWINFO\r\n")


# FUNCTIONS
## Read sensor
def irq_meas(_):
    sensor.readSensor()
    temp.append(sensor.temperature)
    hum.append(sensor.humidity)
    global alarm 
    if (sensor.temperature > TEMP_THR and not alarm) :
        alarm = True
        print(alarm)

## Returns [SINR, RSRP] values as ints
def getSINRandRSRP():
    response = module.sendCommand("AT+QCSQ\r\n")
    while "NBIoT" not in response:
        time.sleep(1)
        response = module.sendCommand("AT+QCSQ\r\n")
        print(response)
    listResp = response.split(",")
    print(listResp)
    RSRP = int(listResp[2]) #bug???
    SINR = int(listResp[3])
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
time = machine.Timer()
time.init(mode=machine.Timer.PERIODIC, period=PERIOD, callback=irq_meas)

while(1):
    if (len(temp) == TOTAL_MEAS_ITER):
        sinr, rsrp = getSINRandRSRP()

        sensor_json_payload = gen_json.gen_json_data(alarm, rsrp, sinr, temp, hum)
        '''
        print("Temperature array:", temp)
        print("------")
        print("Humidity array:", hum)
        print("------")
        '''
        if module.isRegistered():   
            mysocket.send(json_init_payload)
        else:
            print("Not registered")
            # To do: link to register function

        temp.clear()
        hum.clear()
        
        
    