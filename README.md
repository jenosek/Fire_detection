# Fire_detection
## Introduction
The aim of this work is to create a forest fire detector that monitors environment temperature and humidity every 30 minutes. Every 6 hours, these measurements are sent to server. In case of temperature exceeding threshold of 40 °C, detector ignores specified transmission windows and sends alarm warning immediately. False alarm recognition is implemented as well. 

## Wireless technology 
The maximum payload (user data) is relatively small and consists of 24 floats and alarm bit. In addition, the detector is located in remote area. That is why the Narrowband IoT (NB-IoT) technology was selected. Its robustness, good coverage and low consumption will be advantage in this case.

## Transport and application layer
When deciding transport layer, we desired as small overhead as possible. That’s why the UDP was selected. The first approach included also CoAP at application layer for its convenient high level handling, which unfortunately proved troublesome later, as it would require us to define packet format for NB-IoT. On the other hand, by implementing CoAP we would unnecessarily increase the data throughput. That's why we used pure UDP protocol only and received ACK response from proxy server as additionally defined in BG77 library. 

Once sensor measures data, they are sent to ThingsBoard platform by parsing to JSON format. Data payload consists of alarm bit, RSRP (Reference Signal Received Power), SINR (Signal to Interference & Noise Ratio), length of array(s), temperature and humidity arrays. Before any payload can be sent, communication to the ThingsBoard has to be initialized first.

## PSM
Great amount of energy can be saved by putting the BG77 RF module to power sleep mode (PSM) between the 6-hour intervals. Sleep is interrupted when 6 measurements are performed or if one measurement proved to be above alarm's threshold. 

Such long intervals are not appropriate for testing, therefore limiting them to reasonable values will provide us with desired feedback. Proposed ranges of counters were:
-	Active Time: T3324 = 15 s,
-	TAU: T3412 = 5 min = 300 s,  

but network has provided us with:
-	Active Time: T3324 = 2 s,
-	TAU: T3412 = 4200 s.

## Sensor
Temperature and humidity are measured by AHT20 sensor, controlled by I2C bus. Sensor measures temperatures in range from -40 °C to 80 °C with accuracy of +-0.3 °C (temperature) and +-2 % (humidity). Data are then allocated to array. After every successful measurement, temperature is evaluated, whether to fire an alarm or not. 

## Power supply 
Current draw of development kit (board) was measured at 89,4 mA. While in sleep mode the system draws around 200 &micro A. To cover consumption, for instance a solar 600mW solar supplying a pair of Li-Ion batteries (18650) should be used.
