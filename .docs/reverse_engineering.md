# Reverse engineering

### BLE, decompilation? Easy stuff.

Since this is a BLE-based device, I thought it will be as easy as subscribing to the characteristic notifications and reverse engineering the protocol - how difficult can it be for a simple voltage meter in the end?

Subscribing to the characteristic indeed returned a lot of data shown below (one hex line = one notification).

```
3627d57495cb945e11d392c800a28bfa
7afd45c0257438c3dd5e7903a9e82366
ebf79548fa7b7455dbed35901665cfc4
c7c8a16d98268a85d1ac82e7b831ff2b
453c61bbfce776e5d51ff1ab7337959d
```

### Damn, encrypted.

Trying to find any pattern here was unsuccessful, so, probably encrypted.

I hoped I will just decompile the [Android application](https://play.google.com/store/apps/details?id=com.dc.battery.monitor2) .apk, like I used to do, extract the key, find how to decode data and I am done.

Unfortunately, decompiling .apk (with `jadx` and `apktool`) revealed only a few classes + a few native libraries. Not good, but I used to find keys in native libraries already, so I would manage. But, the amount of Java classes after decompilation was way too small.

### Even worse, obfuscated!

I would not expect Chinese developers to code the whole app, including UI in C++ with Android JNI, so in must be some kind of the app obfuscation.

After some googling of the library name (`libjiagu.so`), it indeed turned out that some kind of protector was used, but smart people already found a way to overcome this as well with help of the [Frida](https://github.com/frida/frida) tool.

### Frida to the rescue.

The steps were as follows:

1. download `frida-server` and unpack it,
2. connect to a rooted Android phone with `adb`,
3. copy `frida-server` to the device into `/data/local/tmp` directory (as it doesn't have `noexec` mount option), add `+x` on it and run it,
4. install [frida-dexdump](https://github.com/hluwa/frida-dexdump) on your computer and run it (make sure BM2 app is in the foreground), it should find and download decrypted .dex files from the device memory,
5. use [dex2jar](https://github.com/pxb1988/dex2jar) tool to convert downloaded .dex files into .jar,
6. use [jadx](https://github.com/skylot/jadx) tool to decompile .jar files into Java classes.

### Finally! Java source code

Okay, at this point, we finally have Java source code that we can analyze.

Apparently, Chinese developers like to work with binary data by converting back-and-forth to and from hex format, so the code was slightly cumbersome to read, but eventually I was able to find the AES key.

I extracted whole `AESUtil` class and ran it on the packets list I gathered and got:

```
F550816400FA00000000000000000000
F5507164011300000000000000000000
F5507164012C00000000000000000000
F5508164014500000000000000000000
F5507164015E00000000000000000000
```

much better!

### Done.

First byte `F5` is the packet type, then 3x 4-bit `508` forming the voltage value - `0x0508` = `1288` = 12.88 V. We are done.
