#import serial
import time
import machine


AF_INET=0

SOCK_STREAM = 0
SOCK_DGRAM = 1

SOCK_CLIENT = 0
SOCK_SERVER = 1

SOCK_PUSH_BUFFER = 0
SOCK_PUSH_TERMINAL = 1

COPS_AUTO = 0
COPS_MANUAL = 1
COPS_PREFFERED = 4
COPS_DEREGISTER = 2

RAT_CAT_M_ONLY = 0
RAT_NB_IOT_ONLY = 1
RAT_PREF_CATM = 2

SOCK_STATUS_INITIAL = 0
SOCK_STATUS_OPENING = 1
SOCK_STATUS_CONNECTED = 2
SOCK_STATUS_LISTENING = 3
SOCK_STATUS_CLOSING = 4

class NWInfo:
    def __init__(self, status = 0, RSRP = 0,  RSSI= 0, SINR = 0.0, RSRQ = 0, RAT = "LTE Cat.M", Operator = "", Band = "", EARFCN = 0, TAC = "", CellID = "", ECL="N/A") -> None:
        self.status = status
        self.RSRP = RSRP
        self.RSSI = RSSI
        self.SINR = SINR
        self.RSRQ = RSRQ
        self.RAT = RAT
        self.Operator = Operator
        self.Band = Band
        self.EARFCN = EARFCN
        self.TAC = TAC
        self.CellID = CellID
        self.ECL = ECL

    def __str__(self) -> str:
        return f"Status: {self.status}\r\nRSRP: {self.RSRP} dBm\r\nRSSI: {self.RSSI} dBm\r\nSINR: {self.SINR:.1f} dB\r\nRAT: {self.RAT}\r\nRSRQ: {self.RSRQ} dB\r\nOperator: {self.Operator}\r\nBand: {self.Band}\r\nEARFCN: {self.EARFCN}\r\nTAC: {self.TAC}\r\nCellID: {self.CellID}\r\nECL: {self.ECL}"



class Operator:
    CZ_VODAFONE = "23003"
    CZ_TMOBILE = "23001"
    CZ_O2 = "23002"
    SK_ORANGE = "23101"
    SK_O2 = "23106"
    SK_TMOBILE = "23102"


class BG77:

    echo = True
    rat = 0
    socket_mounted = False

    def __init__(self, serial, verbose = False, radio=True) -> None:
        self.serial = serial
        self.verbose = verbose

        #Reset the modem in case of a MCU restart -> Initializes with default config
        #Only available on UART
        #self.modemSWReset()

        
        if not self.testAT():
            raise OSError("BG77 Init: Cannot get the response from the device.")
        
        if self.setEcho(False):
            self.echo = False
        else:
            raise OSError("BG77 Init: Could not configure Echo.")
        
        if not self.__setCEREG(4):
            raise OSError("BG77 Error setting CEREG")
        
        if not radio:
            self.setRadio(0)
        #serial.write(bytes("AT\r\n","ascii"))
        #a = serial.read(9)
        #print(a)
        #raise "Error BG77 not reachable."

    def __read(self, exit_condition="OK\r\n", timeout = 1) -> str:
        time_start = time.time()
        data_out = ""
        while time.time() < (time_start + timeout):
            data_tmp = self.serial.read(1)
            if data_tmp:
                data_out = data_out + str(data_tmp, 'ascii')
            if exit_condition in data_out:
                break
        return data_out

    def __write(self, cmd :str) -> None:
        self.serial.write(bytes(cmd,"ascii"))

    def sendCommand(self, cmd: str, exit_condition = "OK\r\n", timeout = 1) -> str:
        if self.verbose:
            print(str(time.ticks_ms()) + " -> " + cmd.strip("\r\n"))
        self.__write(cmd)
        '''data_out = ""
        time_start = time.time()
        while time.time() < (time_start + timeout):
            data_tmp = self.serial.read(1)
            data_out = data_out + str(data_tmp, 'ascii')'''
        '''if data_out.__contains__("OK\r\n"):
                break'''
        '''if self.verbose:
            print(cmd.strip("\r\n"))
            print(data_out.strip("b'\r\n"))
        return data_out.strip("b'\r\n")'''
        out = self.__read(exit_condition, timeout).strip("b'\r\n")
        if self.verbose:
            print(str(time.ticks_ms()) + " <- " + out)
        return out
    
    def modemSWReset(self) -> bool:
        ret = self.sendCommand("AT+CFUN=1,1\r\n", exit_condition="RDY\r\n", timeout = 10)
        if "RDY\r\n" in ret:
            return True
        raise OSError("BG77: Modem SW reset failed.")
        #return False

    def testAT(self) -> bool:
        ret = self.sendCommand("AT\r\n")
        if "OK" in ret:
            return True
        return False
    

    def setEcho(self, echo : bool) -> bool:
        if echo:
            ret = self.sendCommand("ATE1\r\n")
        else:
            ret = self.sendCommand("ATE0\r\n")

        if "OK" in ret:
            return True
        return False
    
    def setRadio(self, state: int) -> bool:
        if state == 1 or state == 0 or state == 4:
            ret = self.sendCommand(f"AT+CFUN={state}\r\n", timeout = 2)
        else:
            raise OSError("BG77 Invalid CFUN parameter.")
        if "OK" in ret:
            time.sleep(1)
            return True
        return False
    
    def setOperator(self, mode = COPS_AUTO, op_plmn = Operator.CZ_VODAFONE) -> bool:
        if mode == COPS_AUTO:
            ret = self.sendCommand(f"AT+COPS={mode}\r\n", timeout = 30)
        elif mode == COPS_DEREGISTER or mode == COPS_MANUAL or mode == COPS_PREFFERED:
            ret = self.sendCommand(f"AT+COPS={mode},2,{op_plmn}\r\n", timeout = 30)
        else:
            raise "BG77 Invalid COPS mode."
        
        if "OK" in ret:
            return True
        elif "CME ERROR" in ret:
            return False
        else:
            raise OSError("BG77 Error setting COPS")
        
    def __setCEREG(self, mode:int) -> bool:
        if mode == 0 or mode == 1 or mode == 2 or mode == 4:
            ret = self.sendCommand(f"AT+CEREG={mode}\r\n")
        else:
            raise OSError("BG77 Invalid CEREG mode.")
        return True
    
    def isRegistered(self) -> bool:
        ret = self.sendCommand(f"AT+CEREG?\r\n")
        if "+CEREG" in ret:
            data = ret.strip("+CEREG: ")
            data = data.split(",")
            if data[1] == '1' or data[1] == '5':
                if data[0] == '4':
                    if data[4] == '8':
                        self.rat = 0 #CatM
                    elif data[4] == '9':
                        self.rat = 1 #NB
                return True
        return False
    
    def setAPN(self, apn:str) -> bool:
        ret = self.sendCommand(f"AT+CGDCONT=1,\"IP\",\"{apn}\"\r\n")
        if "OK" in ret:
            return True
        return False
    
    def attachToNetwork(self):
        ret = self.sendCommand(f"AT+CGATT=1\r\n", timeout = 60)
        if "OK" in ret:
            return True
        return False
    
    def detachFromNetwork(self):
        ret = self.sendCommand(f"AT+CGATT=0\r\n", timeout = 60)
        if "OK" in ret:
            return True
        return False
    
    def getNWInfo(self) -> NWInfo:
        #Check if device is registered.
        ret = self.sendCommand(f"AT+CEREG?\r\n")
        if not "+CEREG" in ret:
            return None
        data = ret.strip("+CEREG: ")
        data = data.split(",")
        if not (data[1] == '1' or data[1] == '5'):
            return None

        #Registered at this point
        rat = ""
        if data[4] == '8':
            rat = "LTE Cat.M"
            self.rat = 0
        elif data[4] == '9':
            rat = "NB-IoT"
            self.rat = 1

        nwinfo = NWInfo(status = int(data[1]), RAT=rat, TAC=data[2].strip("\""), CellID=data[3].strip("\""))   

        ret = self.sendCommand(f"AT+QCSQ\r\n")
        if not "+QCSQ" in ret:
            return nwinfo
        data = ret.strip("\r\nOK\r\n")
        data = data.split(",")

        nwinfo.RSSI = int(data[1])
        nwinfo.RSRP = int(data[2])
        nwinfo.SINR = int(data[3])*0.2-20
        nwinfo.RSRQ = int(data[4])

        ret = self.sendCommand(f"AT+QNWINFO\r\n")
        if not "+QNWINFO" in ret:
            return nwinfo
        data = ret.strip("\r\nOK\r\n")
        data = data.split(",")

        nwinfo.Operator = data[1].strip("\"")
        nwinfo.Band = data[2].strip("\"")
        nwinfo.EARFCN = int(data[3])

        return nwinfo
    
    def setRATType(self, rat = 0, immediate_effect = 1) -> bool:
        #If there is a socket mounted do not change RAT otherwise socket will not work.
        if self.socket_mounted:
            return False
        

        if self.rat == 1 and rat == 0: #Narrowband -> CatM
            ret = self.sendCommand(f"AT+QCFG=\"iotopmode\",{rat},{immediate_effect}\r\n")
            if "OK" in ret:
                time.sleep(0.5)
                return True
            return False
        elif self.rat == 0 and rat == 1: #CatM -> Narrowband
            self.setRadio(0)
            time.sleep(1)
            ret = self.sendCommand(f"AT+QCFG=\"iotopmode\",{rat},{immediate_effect}\r\n")
            if "OK" in ret:
                self.setRadio(1)
                time.sleep(1)
                return True
            return False
        return True

    def socket(self, socket_class, socket_protocol, socket_mode = SOCK_CLIENT, socket_push_mode=SOCK_PUSH_BUFFER):
        if not self.isRegistered():
            if self.verbose:
                print("Module is not registered to network. Cannot open socket.")
            return False,None
        if not socket_class == AF_INET:
            if self.verbose:
                print("Incorrect socket_class.")
            return False,None
        if (socket_protocol != SOCK_DGRAM) and (socket_protocol != SOCK_STREAM):
            if self.verbose:
                print("Incorrect socket_protocol. Use SOCK_DGRAM for UDP or SOCK_STREAM for TCP.")
            return False,None
        
        return True, BG77Socket(self, 1, socket_class, socket_protocol, socket_mode, socket_push_mode)
        
    

    

    

    




class BG77Socket:

    timeout=-1

    def __init__(self, bg77: BG77, socket_num, socket_class, socket_protocol, socket_mode, socket_push_mode) -> None:
        self.modem = bg77
        self.socket_num = socket_num
        self.socket_class = socket_class
        self.socket_protocol = socket_protocol
        self.socket_mode = socket_mode
        self.socket_push_mode = socket_push_mode
        self.sock_open = False

    def settimeout(self, to): #to = timeout in s
        if to > 0:
            self.timeout = to*1000
        else:
            self.timeout = -1

    def connect(self, ip="127.0.0.1", remote_port=0, local_port=0):
        socket_protocol = ""
        if self.socket_mode == SOCK_CLIENT:
            if self.socket_protocol == SOCK_DGRAM:
                socket_protocol = "\"UDP\""
            elif self.socket_protocol == SOCK_STREAM:
                socket_protocol = "\"TCP\""
        elif self.socket_mode == SOCK_SERVER:
            if self.socket_protocol == SOCK_DGRAM:
                socket_protocol = "\"UDP SERVICE\""
            elif self.socket_protocol == SOCK_STREAM:
                socket_protocol = "\"TCP LISTENER\""
        
        cmd=f"AT+QIOPEN=1,{self.socket_num},{socket_protocol},\"{ip}\",{remote_port},{local_port},{self.socket_push_mode}\r\n"
        ret = self.modem.sendCommand(cmd)
        if not "OK" in ret:
            return False
        
        #wait for QIOPEN URC
        retry_num = 0
        while retry_num < 10:
            ret = self.modem.__read(exit_condition="\r\n")
            ret = ret.strip("\r\n")
            if self.modem.verbose:
                print(str(time.ticks_ms()) + " <- " + ret)
            if "+QIOPEN" in ret:
                args = ret.strip("+QIOPEN: ")
                args_split = args.split(',')
                if (args_split[1] == '0'):
                    self.sock_open = True
                    return True
                else:
                    print(f"Error opening socket: Error - {args_split[1]}")
                    return False
            retry_num += 1
        return False
    
    def close(self):
        ret = self.modem.sendCommand(f"AT+QICLOSE={self.socket_num}\r\n")
        if "OK" in ret:
            return True
        return False
        
    def sendto(self, remote_ip, remote_port, data):
        pass

    def send(self, data, rai=0):
        if not rai == 0:
            if self.socket_mode == SOCK_SERVER:
                print("Error - Cannot use RAI with socket in SERVER mode.")
                return False
            if len(data) > 512:
                print("Error - Data length has to be less than 512 B to use RAI.")
                return False
            else:
                hex_data = self.__toHex(data)
                ret = self.modem.sendCommand(f"AT+QISENDEX={self.socket_num},\"{hex_data}\",{rai}\r\n",exit_condition="\r\n")
                if self.modem.verbose:
                    print(str(time.ticks_ms()) + " <- " + ret)

        else:
            if len(data) > 1460:
                print("Error - Data length has to be less than 1460 B.")
                return False
            else:
                ret = self.modem.sendCommand(f"AT+QISEND={self.socket_num},{len(data)}\r\n",exit_condition=">")
                ret = self.modem.sendCommand(f"{data}",exit_condition="\r\n")
                if self.modem.verbose:
                    print(str(time.ticks_ms()) + " <- " + ret)

        retry_num = 0
        while retry_num < 10:
            ret = self.modem.__read("\r\n")
            if self.modem.verbose:
                    print(str(time.ticks_ms()) + " <- " + ret)
            if "SEND OK" in ret:
                return True
            elif "SEND FAIL" in ret:
                print("Error sending message. Buffer is full.")
                return False
            elif "ERROR" in ret:
                print("Error sending message. Connection does not exist.")
                return False
            retry_num += 1
        return False


    def recv(self, num_bytes=100):
        #No timeout set
        if self.__dataInBuffer():
            data_len, message = self.__readFromBuffer(num_bytes)
            return data_len, message
        #Inifinite buffer timeout - wait forever
        if self.timeout == -1:
            while True:
                ret = self.modem.__read(exit_condition="\r\n")
                if self.modem.verbose:
                    print(str(time.ticks_ms()) + " <- " + ret)
                if "\"recv\"" in ret:
                    ret = ret.strip("+QIURC: \"recv\",")
                    ret = ret.strip("\r\n")
                    ret_split = ret.split(',')
                    if int(ret_split[0]) == self.socket_num:
                        if self.socket_push_mode == SOCK_PUSH_TERMINAL:
                            data_len = int(ret_split[1])
                            message_response = self.modem.__read(exit_condition="\r\n")
                            message = message_response[:data_len-1]
                            return data_len, message
                        elif self.socket_mode == SOCK_PUSH_BUFFER:
                            data_len, message = self.__readFromBuffer(num_bytes)
                            return data_len, message
        #define timeout for read message
        else:
            start = time.ticks_ms()
            while time.ticks_ms() < start + self.timeout:
                ret = self.modem.__read(exit_condition="\r\n")
                if self.modem.verbose:
                    print(str(time.ticks_ms()) + " <- " + ret)
                if "\"recv\"" in ret:
                    ret = ret.strip("+QIURC: \"recv\",")
                    ret = ret.strip("\r\n")
                    ret_split = ret.split(',')
                    if int(ret_split[0]) == self.socket_num:
                        if self.socket_push_mode == SOCK_PUSH_TERMINAL:
                            data_len = int(ret_split[1])
                            message_response = self.modem.__read(exit_condition="\r\n")
                            message = message_response[:data_len-1]
                            return data_len, message
                        elif self.socket_mode == SOCK_PUSH_BUFFER:
                            data_len, message = self.__readFromBuffer(num_bytes)
                            return data_len, message
        return 0, None


    def getStatus(self):
        ret = self.modem.sendCommand(f"AT+QISTATE\r\n")
        if "+QISTATE: " in ret:
            ret = ret.strip("\r\nOK\r\n")
            ret_field= ret.split("\r\n")
            for open_connection in ret_field:
                in_data = open_connection.strip("+QISTATE: ")
                in_data_split = in_data.split(",")
                if int(in_data_split[0]) == self.socket_num:
                    return int(in_data_split[5])
        return -1
        

    def __dataInBuffer(self) -> bool:
        ret = self.modem.sendCommand(f"AT+QIRD={self.socket_num},0\r\n",exit_condition="\r\n")
        if self.modem.verbose:
            print(str(time.ticks_ms()) + " <- " + ret)
        #ret = self.modem.__read(exit_condition="\r\n")
        retry_num = 0
        while not "+QIRD" in ret:
            ret = self.modem.__read(exit_condition="\r\n")
            if self.modem.verbose:
                print(str(time.ticks_ms()) + " <- " + ret)
            retry_num += 1
            if retry_num > 9:
                return False
            
        ret = ret.strip("\r\n")
        ret = ret.strip("+QIRD: ")
        ret_split = ret.split(',')
        #print(ret_split)
        #Flush the OK from the last transaction
        self.modem.__read()
        if ret_split[2] == '0':
            return False
        return True
    
    def __readFromBuffer(self,data_size):
        ret = self.modem.sendCommand(f"AT+QIRD={self.socket_num},{data_size}\r\n",exit_condition="\r\n")
        if self.modem.verbose:
            print(str(time.ticks_ms()) + " <- " + ret)

        retry_num = 0
        while not "+QIRD" in ret:
            ret = self.modem.__read(exit_condition="\r\n")
            if self.modem.verbose:
                print(str(time.ticks_ms()) + " <- " + ret)
            retry_num += 1
            if retry_num > 9:
                return False
        ret = ret.strip("\r\n")
        ret = ret.strip("+QIRD: ")
        data_len = int(ret)
        message_raw = self.modem.__read(exit_condition="\r\n")
        if self.modem.verbose:
            print(str(time.ticks_ms()) + " <- " + message_raw)
        message = message_raw[:data_len-1]
        #Flush the OK from the last transaction
        self.modem.__read()
        return data_len, message

    def __toHex(self, data):
        hex_str = ""
        for c in data:
            hex_str += f"{ord(c):x}"
        return hex_str
        



    




