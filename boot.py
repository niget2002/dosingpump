import machine
import network
import ssd1306
import wifi
import time

sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.active(True)
    sta_if.connect(wifi.WIFIESSID, wifi.WIFIKEY)
    while not sta_if.isconnected():
        pass
print('network config:', sta_if.ifconfig())

i2c = machine.I2C(-1, scl=machine.Pin(5), sda=machine.Pin(4))
oled_width = 128
oled_height = 32

oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
oled.fill(0)
oled.text("Booting", 0, 0)
oled.text("Tank Doser v0.1", 0, 10)
oled.show()
