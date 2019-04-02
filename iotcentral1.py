import csv
import requests
import gps
import iotc
from sys import argv
from iotc import IOTConnectType, IOTLogLevel


deviceId = "b41665f6-c988-4b3b-955b-707b515b9345"
scopeId = "0ne000435E1"
mkey = "hK3DqfvhoifRmYhbDe09acjOvfAtIuz6mub93kywWk8="

iotc = iotc.Device(scopeId, mkey, deviceId, IOTConnectType.IOTC_CONNECT_SYMM_KEY)
iotc.setLogLevel(IOTLogLevel.IOTC_LOGGING_API_ONLY)


#Listen on port 2947 of gpsd
session = gps.gps("localhost", "2947")
session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)




gCanSend = False
gCounter = 0

def onconnect(info):
  global gCanSend
  print("- [onconnect] => status:" + str(info.getStatusCode()))
  if info.getStatusCode() == 0:
     if iotc.isConnected():
       gCanSend = True

def onmessagesent(info):
  print("\t- [onmessagesent] => " + str(info.getPayload()))

def oncommand(info):
  print("- [oncommand] => " + info.getTag() + " => " + str(info.getPayload()))

def onsettingsupdated(info):
  print("- [onsettingsupdated] => " + info.getTag() + " => " + info.getPayload())

iotc.on("ConnectionStatus", onconnect)
iotc.on("MessageSent", onmessagesent)
iotc.on("Command", oncommand)
iotc.on("SettingsUpdated", onsettingsupdated)

iotc.connect()

while iotc.isConnected():
    rep = session.next()
    try:
        iotc.doNext() # do the async work needed to be done for MQTT
        if gCanSend == True:
            
          #if gCounter == 0:
          #gCounter = 0
          print("Sending telemetry..")

          iotc.sendTelemetry("{ \
\"alt\": " + str(rep.alt) + ", \
\"lon\": " + str(rep.lon) + ", \
\"lat\": " + str(rep.lat) + "}")

        #gCounter += 1
    except Exception as e:
        print('Got expection')
