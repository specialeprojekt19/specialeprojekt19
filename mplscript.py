from smbus import SMBus
import time
import csv
import requests
import iotc
from sys import argv
from iotc import IOTConnectType, IOTLogLevel
import gps
from datetime import datetime
import os

# Special Chars - encoding
deg = u'\N{DEGREE SIGN}'

# I2C Constants
#Addr = the "port" where it is listening on.
ADDR = 0x60
CTRL_REG1 = 0x26
PT_DATA_CFG = 0x13
bus = SMBus(1)

#Set oversample rate to 128, baud rate
setting = bus.read_byte_data(ADDR, CTRL_REG1)
newSetting = setting | 0x38
bus.write_byte_data(ADDR, CTRL_REG1, newSetting)

#Enable event flags
bus.write_byte_data(ADDR, PT_DATA_CFG, 0x07)

#Toggle One Shot
# Set setting for some if statement called bus_write_data
setting = bus.read_byte_data(ADDR, CTRL_REG1)


#check if device is active
who_am_i = bus.read_byte_data(ADDR, 0x0C)
if who_am_i != 0xc4:
    print "Device not active."
    exit(1)

#azure ids and keys
deviceId = "18c521c6-1afd-4084-a7ef-9702158d29b6"
scopeId = "0ne000435E1"
mkey = "8NYpPh6yiEjj4dYBqWQAbLzmi5Bo+sRRjRt5jwRB3Gk="


iotc = iotc.Device(scopeId, mkey, deviceId, IOTConnectType.IOTC_CONNECT_SYMM_KEY)
iotc.setLogLevel(IOTLogLevel.IOTC_LOGGING_API_ONLY)


session = gps.gps("localhost", "2947")
session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

#global counter for failed attempts to send to azure
global a
a = 0

#global checker for connection to azure
global can_send
can_send = False

# Read sensor data
def get_reading():
    global a #tell python that the variable is global and not local
    if (setting & 0x02) == 0:
        bus.write_byte_data(ADDR, CTRL_REG1, (setting | 0x02))
    
    #pressure data reads from the addr 1..
    #temp data reads from the addr 04...
    #then we get a new status for the bus
    p_data = bus.read_i2c_block_data(ADDR,0x01,3)
    t_data = bus.read_i2c_block_data(ADDR,0x04,2)

    #different variables to calculate pressure
    p_msb = p_data[0]
    p_csb = p_data[1]
    p_lsb = p_data[2]

    #different variables to calcuate temperatuer
    t_msb = t_data[0]
    t_lsb = t_data[1]

    #calcuate pressure, p_decimal and temperature
    pressure = (p_msb << 10) | (p_csb << 2) | (p_lsb >> 6)
    p_decimal = ((p_lsb & 0x30) >> 4)/4.0
    pressure_with_decimal = str(pressure + p_decimal)
    celsius = t_msb + (t_lsb >> 4)/16.0
    time_read = str(time.strftime('%m/%d/%Y %H:%M:%S%z'))

    global latitude
    global longitude

    write_to_csv(pressure_with_decimal, celsius, latitude, longitude, time_read)
    

    global can_send
    if can_send == True:
        send_to_azure(pressure_with_decimal, celsius, latitude, longitude)
    else:
        send_to_azure(pressure_with_decimal, celsius, latitude, longitude)
        #print('Failed to run send_to_azure')
        #a += 1 #plus 1 to global counter in regular_run_script because isConnect = false

#New Insert
def write_to_csv(pressure_with_decimal, celsius, latitude, longitude, time_read):
    current_date = time.strftime("%Y-%m-%d-%H-%M")
    path = time.strftime("%Y-%m-%d-%H")
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, current_date), 'a') as file:
        headers = ["pressure", "celsius", "latitude", "longitude", "time"]
        writer = csv.DictWriter(file, headers)
        writer.writerow({'pressure':pressure_with_decimal, 'celsius':celsius, "latitude":latitude, "longitude":longitude, 'time':time_read})
        print('Saved to CSV')

#Old CSV write
#def write_to_csv(pressure_with_decimal, celsius, latitude, longitude, time_read):
 #   current_date = time.strftime("%Y-%m-%d-%H")
  #  with open(current_date, "a") as file:
   #     headers = ["pressure", "celsius", "latitude", "longitude", "time"]
    #    writer = csv.DictWriter(file, headers)
     #   writer.writerow({'pressure':pressure_with_decimal, 'celsius':celsius, "latitude":latitude, "longitude":longitude, 'time':time_read})
      #  print('Saved to CSV')

def connect_to_azure():
    try:
        iotc.connect()
    except Exception as e:
        print(e)


def onconnect(info):
    global can_send
    if info.getStatusCode() == 0:
        if iotc.isConnected():
            print("connected!")
            can_send = True
    else:
        print('you basket case')


def send_to_azure(pressure_with_decimal, celsius, latitude, longitude):
    iotc.doNext()
    pressure = pressure_with_decimal
    try:
        iotc.sendTelemetry("{ \
\"pressure_read\": " + str(pressure) + ", \
\"lon\": " + str(longitude) + ", \
\"celsius\": " + str(celsius) + ", \
\"lat\": " + str(latitude) + "}")
        print('Send telemetry')
    except Exception as e:
        print('error')

 #Attempt to connect to azure and send variables for every 10th sec
def main():
    connect_to_azure()
    iotc.on("ConnectionStatus", onconnect)
    b = 0                 #local counter
    global longitude
    global latitude
    latitude = 'N/A'
    longitude = 'N/A'
    while b < 2:
        t1 = datetime.now()
        while (datetime.now()-t1).seconds <= 10:
            try:
                rep = session.next()
                if rep['class'] == 'TPV':
                    if hasattr(rep, 'lat'):
                        latitude = rep.lat
                    if hasattr(rep, 'lon'):
                        longitude = rep.lon
            except:
                print('expecto!')
        get_reading()

        #regular_run_script()    #run the regular_run_script (rss)
        #b += 1                   #when rrs has through (i.e. tried to connect to azure) = +1. After 30 times of running rss then reboot
        #print("b = " + str(b)) 



    print("reboot here")





main()

