"""
main.py
"""

import utime
import machine
import ssd1306
import network
import ubinascii
import ujson

import onewire
import ds18x20

try:
    import usocket as socket
except:
    import socket
import uselect as select

import ntp
from dst import dst_time


import gc
gc.collect()

# Hardware Setup

# setup OLED interface
i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4))
DEVICEID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
OLED = ssd1306.SSD1306_I2C(128, 32, i2c)

# setup Temp Probe
ds_pin = machine.Pin(2)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

roms = ds_sensor.scan()
print('Found DS devices: ', roms)
ds_sensor.convert_temp()

# grab WiFi Settings
sta_if = network.WLAN(network.STA_IF)

# setup Timing
temp_interval = 5000
screen_interval = 1000

# setup pump
pump = machine.Pin(14, machine.Pin.OUT)

# Setup Web Page
def web_page():
    global data
    if pump.value() == 1:
        gpio_state="ON"
    else:
        gpio_state="OFF"


    html = """<html><head> <title>Dosing Pump Controller</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,"> <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
    h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none;
    border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
    .button2{background-color: #4286f4;}</style></head>
    <body><h1>Dosing Pump Setup</h1>
    <p>PUMP state: <strong>""" + gpio_state + """</strong></p>
    <p>Current Start Time: """ + str(data['pump_hour']) + """:""" + str(data['pump_min']) + """</p>
    <p><form action="/?settime">Set Start Time</p>
    <p><input type=text id=phour name=phour size=2>:<input type=text id=pmin name=pmin size=2><input type=submit value=submit></form></p>
    <p>Current Run Length: """ + str(data['pump_runtime']) + """</p>
    <p>Callibrate Run Length</p>
    <p><a href="/?pump=on"><button class="button">Callibrate Start</button></a></p>
    <p><a href="/?pump=off"><button class="button button2">Callibrate Stop</button></a></p>
    <p><a href="/?prime=on"><button class="button">Prime Start</button></a></p>
    <p><a href="/?prime=off"><button class="button button2">Prime Stop</button></a></p>
    </body></html>"""
    return html

# Setup Socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

data = {'pump_hour': 12, 'pump_min':0, 'pump_runtime':0}

def json_read():
    # grab config from json
    global data
    global pump_hour
    global pump_min
    write_values=0
    try:
        json_data_file = open('config.json', 'r')
        data = ujson.loads(json_data_file.read())
        json_data_file.close()
    except:
        print("Cloud not read config file")
        json_write()
    if data.get('pump_hour')==None:
        data['pump_hour'] = 12
        write_values=1
    if data.get('pump_min')==None:
        data['pump_min'] = 0
        write_values=1
    if data.get('pump_runtime')==None:
        data['pump_runtime'] = 10
        write_values=1
    if write_values:
        json_write()
    print(data)

# Setup Json Write
def json_write():
    """ Writes global data value to config file """
    global data
    try:
        json_data_file = open('config.json', 'w')
        json_data_file.write(ujson.dumps(data))
        json_data_file.close()
    except Exception as e:
        print("Could not update config file")


# Function initilization
def print_screen(data0, data1, data2):
    """prints data to the OLED"""
    global data
    OLED.fill(0)
    OLED.text(sta_if.ifconfig()[0], 0, 0)
    OLED.text(data0, 0, 10)
    OLED.text(data1, 50, 10)
    OLED.text(data2, 0, 20)
    OLED.show()

def c_to_f(c):
    return round(c*(9/5)+32)

def qs_parse(qs):
    parameters = {}
    spaceSplit = qs.split(" ")
    matching = [s for s in spaceSplit if "phour" in s]
    ampersandSplit = matching[0].split("&")
    for element in ampersandSplit:
        equalSplit = element.split("=")
        parameters[equalSplit[0].replace('/?','')] = equalSplit[1]
    return parameters

def main():
    """main loop function"""

    # Initilize local variables
    global data
    temp_start = utime.ticks_ms()
    screen_start = utime.ticks_ms()
    callibrate_start = temp_start # Initilize value in case website is in bad state
    time = dst_time()
    pump_run = 1 # allows pump to run 1 time at next iteration
    next_runtime = str(data['pump_hour'])+':'+str(data['pump_min'])

    temperature = "NOTEMP"

    while 1:
        if utime.ticks_diff(utime.ticks_ms(), temp_start) > temp_interval:
            temperature = str(c_to_f(ds_sensor.read_temp(roms[0])))
            ds_sensor.convert_temp()
            temp_start = utime.ticks_ms()
        if utime.ticks_diff(utime.ticks_ms(), screen_start) > screen_interval:
            time = dst_time()
            this_time = str(time[3])+':'+str(time[4])
            print_screen(this_time, next_runtime, temperature)
            screen_start = utime.ticks_ms()

        if (time[3] == int(data['pump_hour'])) and (time[4] == int(data['pump_min'])):
            if pump_run:
                pump.value(1)
                print_screen(this_time, 'Pump On', temperature)
                print(data['pump_runtime'])
                utime.sleep_ms(data['pump_runtime']) # this is a blocking command, but shouldn't be an issue.
                pump.value(0)
                print_screen(this_time, next_runtime, temperature)
                pump_run = 0
        else:
            pump_run = 1

        r, w, err = select.select((s,), (), (), 1)
        if r:
            for readable in r:
                conn, addr = s.accept()
                print('Got a connection from %s' % str(addr))
                request = conn.recv(1024)
                request = str(request)
                print('Content = %s' % request)
                pump_on = request.find('/?pump=on')
                pump_off = request.find('/?pump=off')
                prime_on = request.find('/?prime=on')
                prime_off = request.find('/?prime=off')
                set_time = request.find('/?phour')
                if pump_on == 6:
                    print('LED ON')
                    pump.value(1)
                    callibrate_start = utime.ticks_ms()
                if pump_off == 6:
                    print('LED OFF')
                    pump.value(0)
                    callibrate_stop = utime.ticks_ms()
                    data['pump_runtime'] = callibrate_stop - callibrate_start
                    json_write()
                if prime_on == 6:
                    print('LED ON')
                    pump.value(1)
                if prime_off == 6:
                    print('LED OFF')
                    pump.value(0)
                if set_time == 6:
                    parameters = qs_parse(request)
                    print(parameters)
                    data['pump_hour'] = parameters['phour']
                    data['pump_min'] = parameters['pmin']
                    next_runtime = str(data['pump_hour'])+':'+str(data['pump_min'])
                    print(data)
                    json_write()

                response = web_page()
                conn.send('HTTP/1.1 200 OK\n')
                conn.send('Content-Type: text/html\n')
                conn.send('Connection: close\n\n')
                conn.sendall(response)
                conn.close()

print_screen('Initializing', '', '...')
ntp.settime()
time = dst_time()
print(time)
json_read()
main()
