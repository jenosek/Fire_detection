import machine
import BG77
import time


class RADIO:
    def __init__(self):
        ## UART Handler
        self.bg_uart = machine.UART(0, baudrate=115200, tx=machine.Pin(0), rxbuf=256, rx=machine.Pin(1), timeout = 0, timeout_char=1)
        
        ## Initialize Radio (HW)
        self.bg_uart.write(bytes("AT\r\n","ascii"))
        print(self.bg_uart.read(10))

        ## Radio Module Class Init
        self.module = BG77.BG77(self.bg_uart, verbose=True, radio=False)
        time.sleep(3)



    def connect_radio(self):
        self.module.setRadio(0)
        self.module.sendCommand("AT+QCFG=\"band\",0x0,0x80084,0x80084,1\r\n")
        self.module.setRadio(1)
        self.module.setAPN("lpwa.vodafone.iot")
        self.module.sendCommand("AT+QCSCON=1\r\n")
        time.sleep(3)
        self.module.setRadio(1)
        resp = self.module.sendCommand("AT+QNWINFO\r\n")
        while "NBIoT" not in resp:
            time.sleep(3)
            self.module.sendCommand("AT+COPS=1,2,23003\r\n")
            resp = self.module.sendCommand("AT+QNWINFO\r\n")