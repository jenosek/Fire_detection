import machine
import time
import uselect, sys
import BG77
import _thread
import os
import gen_json
#from coap import microcoapy
#from coap import coap_macros as macros

DEV_ID = 24
FW_VER = "1.0.0"
MAN = "VUT Brno"
GPS = [49.2267250, 16.5743461]

AccessT = "2njiwhpsv38zc0i49214"
DevID = "14279d50-1f84-11f0-9037-29f37c847020"

#IP_ADDRESS = "147.229.148.105"
IP_ADDRESS = "62.245.74.185"
PORT = 63404
#PORT = 5683
_COAP_POST_URL = f'api/v1/{AccessT}/telemetry'

# INIT COAP CLIENT 
#client = microcoapy.Coap()
#client.debug = True



spoll=uselect.poll()
spoll.register(sys.stdin,uselect.POLLIN)
pon_trig = machine.Pin(9,machine.Pin.OUT)

# wake up radio module
pon_trig.value(1)
time.sleep(.3)
pon_trig.value(0)
time.sleep(5)

bg_uart = machine.UART(0, baudrate=115200, tx=machine.Pin(0), rxbuf=256, rx=machine.Pin(1), timeout = 0, timeout_char=1)

bg_uart.write(bytes("AT\r\n","ascii"))
print(bg_uart.read(10))


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

print("Terminal Ready")

def read1():
    return(sys.stdin.read(1) if spoll.poll(0) else None)

def readline():
    c = read1()
    buffer = ""
    while c != None:
        buffer += c
        c = read1()
    return buffer

### returns [SINR, RSRP] values as ints
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
    return [SINR, RSRP]


### returns List of strings Radio_values = ["NB-IoT", CELL_ID, Tracking Area Code, Band, EARFCN]
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

def create_coap_payload(confirmable, uri, json_payload):
    version = 1
    type = 0 if confirmable else 1 # 0 for CON, 1 for NON
    token_length = 0
    code = 2 # POST method
    message_id = 12345

    # Create the header
    header = (version << 6) | (type << 4) | token_length
    header_bytes = struct.pack('!BBH', header, code, message_id)

   
    

    # Construct the full message
    coap_message = header_bytes + b'\xff' + json_payload

    return coap_message


json_init_payload = gen_json.gen_json_init(getStartInfo(), GPS, DEV_ID, FW_VER, MAN)



'''
Opening UDP socket
'''
success, mysocket = module.socket(BG77.AF_INET, BG77.SOCK_DGRAM, BG77.SOCK_CLIENT, BG77.SOCK_PUSH_BUFFER)
mysocket.connect(IP_ADDRESS, PORT, 0)
if module.isRegistered():   
    mysocket.send(json_init_payload)


while True:
    try:
        data = readline()
        if len(data) != 0:
            if "WKUP" in data.upper():
                pon_trig.value(1)
                time.sleep(.3)
                pon_trig.value(0)
            elif "TIME" in data:
                print(time.ticks_ms())
            elif "STOP" in data:
                os.exit()
            else:
                print(f"{time.ticks_ms()}: -> " + data.strip("\r\n"))
                bg_uart.write(data[:len(data)-2].encode())
                bg_uart.write("\r\n")
        if bg_uart.any():
            time.sleep(.01)
            data = bg_uart.read()
            #print(data)
            if data != None:
                #data = data.decode()
                #print(data)
                if 0xff in data:
                    m = bytearray(data)
                    for i in range(len(m)):
                        if m[i] == 0xff:
                            m[i] = 0
                    data = bytes(m)
                data = str(data, 'ascii')
                data = data.strip('\r\n')
                data_split = data.split("\n")
                for line in data_split:
                    if line == "\r\n":
                        continue
                    print(f"{time.ticks_ms()}: <- {line.strip('\r\n')}")
        time.sleep(.1)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(e)
        
    
    
    