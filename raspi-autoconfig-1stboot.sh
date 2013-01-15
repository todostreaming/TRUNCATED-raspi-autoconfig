#!/bin/sh
# Part of raspi-autoconfig http://github.com/shamiao/raspi-autoconfig
#
# See LICENSE file for copyright and license details

# Should be installed to /etc/profile.d/raspi-autoconfig-1stboot.sh to force raspi-autoconfig
# to run at initial login

# You may also want to set automatic login in /etc/inittab on tty1 by adding a
# line such as:
# 1:2345:respawn:/bin/login -f root tty1 </dev/tty1 >/dev/tty1 2>&1 # RPICFG_TO_DISABLE

if [ $(id -u) -ne 0 ]; then
  printf "\nNOTICE: the software on this Raspberry Pi has not been fully configured. Please run 'sudo raspi-autoconfig'. \n\n"
else
  raspi-autoconfig.py
  if [ $? -ne 0 ]; then
    raspi-config
  fi
  exec login -f pi
fi
