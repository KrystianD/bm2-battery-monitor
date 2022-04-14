BM2 Battery Monitor
======

Result of my reverse engineering work on Bluetooth-based car battery monitor.

[Battery Monitor 2](https://play.google.com/store/apps/details?id=com.dc.battery.monitor2) on Google Play

Python MQTT publisher + ESPHome template.

## Python MQTT publisher - Usage

```shell
python bm2_mqtt.py \
    --mqtt-host localhost \
    --mqtt-port 1883 \
    --mqtt-topic bm2 \
    --bm2-addr B0:B1:xx:xx:xx:xx
```

## Reverse engineering

If you are curious on how I did the reverse engineering process, [read here](.docs/reverse_engineering.md).

## Keywords
BM2, Battery Monitor 2, com.dc.battery.monitor2, ICS Technology, Intelligent Control System
