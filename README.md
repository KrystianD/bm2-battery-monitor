BM2 Battery Monitor
======

Result of my reverse engineering work on Bluetooth-based car battery monitor.

[Battery Monitor 2](https://play.google.com/store/apps/details?id=com.dc.battery.monitor2) on Google Play

## Content

### `bm2_python` - Python client library

Supports the following API calls:
* Reading current voltage - `BM2Client.get_voltage()`
* Reading voltages history - `BM2Client.get_history()`

### `bm2_esphome` - ESPHome template exposing current voltage

### `apps` - Example applications

* `bm2_viewer.py` - data viewer
* `bm2_history.py` - history reader
* `bm2_mqtt.py` - mqtt sender

## Python library usage

```python
import asyncio

from bm2.client import BM2Client

async def main():
    bm2 = BM2Client("B0:B1:xx:xx:xx:xx")
    bm2.start()
    
    # Read historical measurements
    history_readings = await bm2.get_history()
    
    for history_reading in history_readings:
        date_str = history_reading.date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{date_str} = {history_reading.voltage} V")

    # Read current voltage measurements
    while True:
        voltage = await bm2.get_voltage()
        print(voltage)

asyncio.run(main())
```

## Example apps

Install dependencies from `apps/requirements.txt` - best in a virtualenv, then:

```shell
python apps/bm2_viewer.py --bm2-addr B0:B1:xx:xx:xx:xx

python apps/bm2_history.py --bm2-addr B0:B1:xx:xx:xx:xx

python apps/bm2_mqtt.py 
    --mqtt-host localhost \
    --mqtt-port 1883 \
    --mqtt-topic bm2 \
    --bm2-addr B0:B1:xx:xx:xx:xx
```

## Reverse engineering

If you are curious on how I did the reverse engineering process, [read here](.docs/reverse_engineering.md).

## Keywords
BM2, Battery Monitor 2, com.dc.battery.monitor2, ICS Technology, Intelligent Control System
