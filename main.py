import machine
import radio
import tmplib as TMP
import uselect, sys
import time
import BG77
import gen_json
from PSM import PSM
import _thread

global thread2active
def core2_task():
    import machine
    global thread2active
    thread2active = True
    sel0 = machine.Pin(2, machine.Pin.OUT)
    sel1 = machine.Pin(3, machine.Pin.OUT)

    sel0.value(0)
    sel1.value(1)

    adc = machine.ADC(0)

    uart = machine.UART(1, baudrate=115200, tx=machine.Pin(4), rx=machine.Pin(5))
    VREF=3.3
    while thread2active:
        read_adc = adc.read_u16()
        '''
        if read_adc > 65000:
            sel0.value(1)
        elif read_adc < 42000:
            sel0.value(0)
        '''
        #print(str(read_adc))
        uart.write(str(time.ticks_ms())+ "," + str(read_adc)+"\r")
        time.sleep(0.001)
    print("second thread terminated")
        
second_thread = _thread.start_new_thread(core2_task, ())


# CONSTANTS
## MEASURING
I2C_SDA = 14
I2C_CLK = 15
SENSOR_ADDRESS = 56
TEMP_THR = 30
PERIOD = 10000
TOTAL_MEAS_ITER = 5
ACK_MESSAGE_LENGTH = 2

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

radio_module = radio.RADIO()
module = radio_module.module
radio_module.connect_radio()

bg_uart = machine.UART(0, baudrate=115200, tx=machine.Pin(0), rxbuf=256, rx=machine.Pin(1), timeout = 0, timeout_char=1)

bg_uart.write(bytes("AT\r\n","ascii"))
print(bg_uart.read(10))



## Initialize PSM

psm = PSM(module, pon_trig, PSM.TAU_5_minutes, PSM.ACTIVE_2_seconds)

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
    while "NBIoT" not in response and len(response.split(","))<3:
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
    while "NBIoT" not in response and len(response.split(","))<3:
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
timer = machine.Timer() # type: ignore
timer.init(mode=machine.Timer.PERIODIC, period=PERIOD, callback=irq_meas)
mainThread = True
while(mainThread):
    try:
        if (len(temp) >= TOTAL_MEAS_ITER or notify_alarm):
            
            '''
            print("Temperature array:", temp)
            print("------")
            print("Humidity array:", hum)
            print("------")
            '''

            
            if module.isRegistered():
                sinr, rsrp = getSINRandRSRP(module)

                sensor_json_payload = gen_json.gen_json_data(alarm, rsrp, sinr, temp, hum)   
                mysocket.send(sensor_json_payload)

                data_len, message = mysocket.recv(ACK_MESSAGE_LENGTH)
                if data_len == 0:
                    print("Message not delivered")

                else:  
                    print(f"Rx message: {message}")    
                    temp.clear()
                    hum.clear()
                    notify_alarm = False

            else:
                print("Not registered")
                psm.wakeup()
                module.sendCommand("AT+CEREG=4\r\n")
                module.setRadio(1)
                module.sendCommand("AT+CEREG?\r\n")
                module.sendCommand("AT+QNWINFO\r\n")
                module.sendCommand("AT+QIACT=1\r\n")
                module.sendCommand("AT+QISTATE\r\n")
                
                mysocket.close()
                time.sleep(2)
                mysocket.connect(IP_ADDRESS, PORT, 0)
                #mysocket.connect(IP_ADDRESS, PORT, 0)
                
                #radio_module.connect_radio()
    except KeyboardInterrupt:
        thread2active = False
        mainThread = False
        print("Threads terminated")
print("Main thread terminated")   