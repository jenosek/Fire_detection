import machine
import time

#Class holding all the variables and methods
class AHT20:
    #Here, variables in the scope of the class are defined
    temperature = 0
    humidity = 0
    i2c_handler = None
    address = 0
    
    #Constructor - Code is automatically executed on creation of the object
    #@Param i2c_handler - Handler of the hardware I2C protocol peripheral.
    #@Param address		- address of the sensor.
    #@Returns - None
    def __init__(self, i2c_handler, address):
        #Save the references to the handler and address
        self.i2c_handler = i2c_handler
        self.address = address
        
        #Initialize sensor according to the datasheet
        data = b'\xBE\x08\x00'
        self.i2c_handler.writeto(self.address, data)
        time.sleep_ms(40)
        
    #readSensor - Function initializes measurement, reads data, converts them
    #to a human readable form and saves them in variables in scope of the object
    #@Param 	- None
    #@Returns 	- None
    def readSensor(self):
        #Initialize measurement according to the datasheet
        data = b'\xAC\x33\x00'
        self.i2c_handler.writeto(self.address, data)
        
        #Wait for a specified amount of time + extra (from the datasheet)
        time.sleep_ms(100)
        
        #Read data from the sensor (7 bytes) -> according to the datasheet
        output = self.i2c_handler.readfrom(self.address,7)
        
        #Convert values from sensor (temperature, humidity into their respective
        # 20-bit (8+8+4 for each) numbers according to the datasheet
        hum_val = (output[1] << 12) | (output[2] << 4) | (output[3] >> 4)
        tmp_val = ((output[3] & 0x0F) << 16) | (output[4] << 8) | output[5]
        
        #Covert values into human readable form and save them into variables
        # in the scope of the object.
        self.humidity = (hum_val/(2**20))*100
        self.temperature = (tmp_val/(2**20))*200 - 50