raspi-autoconfig Configuration File Guide
================
`raspi-autoconfig` uses `autoconfig.ini` in the FAT32 boot partition of SD card to change miscellaneous settings of your Raspberry Pi and Raspbian system. 

`raspi-autoconfig` runs only if a valid `autoconfig.ini` exists in the FAT32 boot partition. 

`autoconfig.ini` provides following settings: 

Screen Settings [Screen]
----------------
This part customizes Raspberry Pi's screen display. Settings here are recognized and written into `config.txt` file. 

### Resolution
Set screen resolution. 

Normally, Raspberry Pi detects the resolutions of target device automatically. But for some devices, especially HDMI->VGA converter, Raspberry Pi is unable to determine right resolution, results in a significantly large or small graphic. 

Specify a resolution manually may solve this problem. 

Available values:

* `Auto`: Detect resolution automatically. (Raspberry Pi default behavior)
* `hdmi_group, hdmi_value`: Specify resolution manually.   
  For example: `2, 9` represents 800x600 @ 60Hz. 

For a complete list of available hdmi\_group and hdmi\_value settings, see: [Video mode options - RPiconfig - eLinux.org](http://elinux.org/RPiconfig#Video_mode_options). 

### Output
Set output device.

Normally Raspberry Pi send video signal to HDMI port if a HDMI device exists. But for few devices, Raspberry Pi is unable to sense its existance and uses composite video instead. 

For that situation, set this option to "HDMI" to force HDMI output. 

You may set this option to "Comp" to ignore any HDMI devices too. 

Available options:

* `Auto`: Use HDMI if a HDMI device is plugged in. (Raspberry Pi default behaviour)
* `HDMI`: Forced HDMI output. 
* `Comp`: Forced composite output, ignore any HDMI device plugged in. 

Wired Ethernet [Wired]
----------------
This part customizes Raspberry Pi's wired network.  

Note: Settings of this part works for both Raspberry Pi B Model integrated wired network, and any USB wired network card, which can be automatically recognized by Raspbian system. 

But these settings will be applied to only ONE UNSPECIFIED network card. With multiple network card plugged in, the result will be unpredictable. 

Make sure ONLY ONE wired network card, including integrated one, is plugged in your Pi. 

### DHCP
Enable of disable DHCP (aka. IP address automattic detection). 

Available options:

* `1`: Enable DHCP, detect IP address automatically. (Raspbian default behaviour)
* `0`: Disable DHCP, assign IP address manually. 

### IP address, subnet mask and default gateway
Assigns IP address manually with these settings. Available only if `DHCP=0`. 

Example:

* `IP=192.168.0.52`
* `Subnet=255.255.255.0`
* `Gateway=192.168.0.1`

Wi-Fi [Wireless]
----------------
This part customizes Raspberry Pi's USB Wi-Fi dongles.  

Note: As the same as wired network cards, make sure ONLY ONE USB Wi-Fi dongle is plugged in your Pi. 

### SSID and Passphrase
Assign Wi-Fi SSID and paraphrase. Open, WEP, WPA and WPA2 supported. (Passphrase option is not needed for Open network)

Example: 

* `SSID=BobHome`
* `Passphrase=mypassword`

### DHCP and IP address settings
The same as wired network settings. 

Localization settings [Locale]
----------------
This part localizes your Raspbian system. 

### Available locales and default language
Set default language, and supported languages for your Raspbian system. The settings here are the same as `locale` settings in `raspi-config`.

Refer to [RPi locale - eLinux.org](http://elinux.org/RPi_locale) for a complete list of available languages. 

The same languages may have multiple different options using different text encoding. UTF-8 is __STRONGLY RECOMMENDED__. 

Available options:

* `Locale`: A list of supported languages. separated by comma.   
  Example: `Locale=en_US.UTF-8 zh_CN.UTF-8`
* `DefaultLocale`: Default language, must exists in supported languages.   
  Example: `DefaultLocale=en_US.UTF-8`

### Keyboard model layout
Keyboard settings include 2 parts: __hardware__ model, and __software__ layout. For example: For a same 104-key keyboard hardware, either QWERTY or Dvorak layout may be used. 

Default keyboard layout for Raspbian system is English (UK), this may cause confusions to US and Chinese users. 

For a list of available model and layout values, see: [RPi Keyboard layout - eLinux.org](http://elinux.org/RPi_Keyboard_Layout). 

Available options: 

* `KeyboardModel`: Keyboard hardware model. 
* `KeyboardLayout`: Keyboard software layout. 

Tip: US users can set `KeyboardModel=pc104` and `KeyboardLayout=us`. 

### Time zone
Set a time zone in "Area/Location" format. 

Refer to tz database for all available values: [List of tz database time zones - Wikipedia](http://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

Example:

* `Timezone=America/New_York`

APT software manager [APT]
----------------
### Mirror setting
Normally Raspbian uses a mirror director, to redirect to one of mirror servers.

This results in slow connection sometimes. It's recommended to specify a mirror server fast for your local network manually. 

For a complete list of all available mirrors, see: [RaspbianMirrors - Raspbian](http://www.raspbian.org/RaspbianMirrors).   
It's especially recommended for Chinese users to use any Korean mirror server, rather than China server provided by Tsinghua - CERNET used in China universities is often very slow for public network users. 

Example:

* `Mirror=http://ftp.kaist.ac.kr/raspbian/raspbian/`

Remote access (SSH & VNC) [Remote]
----------------
(TBC.)

Simplified Chinese Localization [SimpChinese]
----------------
(TBC.)
