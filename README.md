raspi-autoconfig
================

Automatic (non-interactive) config tool for Raspbian on Raspberry Pi &reg; ARM computer. 

With original `raspi-config` tool, user has to specify various settings all by himself every time installs Raspbian. This is very inconvient, especially in a no monitor "headless" usage with network not properly configured. 

Instead, `raspi-autoconfig` customize Raspbian by editing a simple `.ini` file on your computer. Config Raspbian by `raspi-autoconfig` is just a simple case of edit, copy & paste. 

This program provides several useful settings that `raspi-config` doesn't have, including static IP address, Wi-Fi connection, and APT mirror customization. 

Features
----------------

### Ordinary raspi-config functions
* Expand root partition to fill SD card (expand_rootfs)
* Localization: locales, keyboard model and layout, timezone
* Enable/disable SSH

### Brand new functions
* Screen: resolution and output device
* DHCP or static IP address for onboard wired network
* Wi-Fi: set SSID and password for USB Wi-Fi dongles, WEP/WPA/WPA2 encryption supported. 
* APT: specify APT mirror site URL manually
* Remote desktop: install VNC and start it on boot
* Simplified Chinese: Wenquanyi font, SCIM Pinyin/Wubi input method

Installation
----------------

1. Mount 2 partitions (a FAT32 and an Ext4) on your SD card. 
2. Put `raspi-autoconfig.py` into `/usr/sbin/`. 
3. Put `bootup-raspi-autoconfig.sh` into `/etc/profile.d/`. 
4. Remove `/etc/profile.d/raspi-config.sh`. 
5. Put `autoconfig.ini` into the FAT32 bootup partition. 
6. Edit `autoconfig.ini`. Necessary directions are included. 
7. Insert SD card into your Pi and power on. 

`raspi-autoconfig` runs on first startup instead of `raspi-config`. If you have a monitor, you may see the progress. 

Raspberry Pi will be ready to use when all configuration process completed. 

### Image file patch for Windows users

Step 1-4 is impossible for Windows users because Linux Ext4 partitions cannot be read or write on Windows. 

For Windows users, a patch is provided to convert original Raspbian image into image with `raspi-autoconfig` included. 

Windows users may follow these steps:

1. Download patch toolkit in `image_path` directory.
2. Extract to the same directory of `20xx-xx-xx-wheezy-raspbian.img`.
3. Execute `patch.cmd`, a new image file will be generated. 
4. Write the new image file to SD card. 
5. Follow the step 5-7 above. 

Note: the patch is in xdelta3 format. Linux users may use the patch to create patched image file too. 

