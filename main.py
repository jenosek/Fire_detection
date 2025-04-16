import machine
#import coap_macros
import tmplib as TMP

# CONSTANTS
I2C_SDA = 14
I2C_CLK = 15
SENSOR_ADDRESS = 56
TEMP_THR = 20
PERIOD = 2000
TOTAL_MEAS_ITER = 5

# ARRAYS
temp = []
hum = []

# VARIABLES
global alarm
alarm = False


# HANDLERS AND INITS
## I2C Handler
i2c_handler = machine.I2C(1, sda=machine.Pin(I2C_SDA), scl=machine.Pin(I2C_CLK), freq=100000)

## Initialize AHT20
sensor = TMP.AHT20(i2c_handler, SENSOR_ADDRESS)

# FUNCTIONS
def irq_meas(_):
    sensor.readSensor()
    temp.append(sensor.temperature)
    hum.append(sensor.humidity)
    global alarm 
    if (sensor.temperature > TEMP_THR and not alarm) :
        alarm = True
        print(alarm)
        

## Timer
time = machine.Timer()
time.init(mode=machine.Timer.PERIODIC, period=PERIOD, callback=irq_meas)

while(1):
    if (len(temp) == TOTAL_MEAS_ITER):
        print("Temperature array:", temp)
        print("------")
        print("Humidity array:", hum)
        print("------")
            
        temp.clear()
        hum.clear()
        
        
    