#! /usr/bin/env python3

# raspi-autoconfig 1.0
#
# Automatic (non-interactive) config tool for Raspbian on Raspberry Pi(R) 
# ARM computer. 
# 
# Project homepage: http://github.com/shamiao/raspi-autoconfig
# View README.md file for help. 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

############################################################
############  G L O B A L   V A R I A B L E S  #############
############################################################

import sys # Import globally: for stderr output

# Splash screen shown at launch of program 
RPAC_SPLASH_STRING = '''\

************************************************************
   raspi-autoconfig 1.0
   Automatic configuration tool for Raspberry Pi (R)
   
   http://github.com/shamiao/raspi-autoconfig
************************************************************
   
'''

# Regex validation rules for configuration file
RPAC_CONFIG_REGEX = {
    'Screen': {
        'Resolution': '^((1,\\s+\\d+)|(2,\\s+\\d+))$', # unsafe match
        'Output': '^(Auto|HDMI|Comp)$'
    }, 
    'Wired': {
        'DHCP': '^(1|0)$',
        'IP': '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', # unsafe match
        'Subnet': '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', # unsafe match
        'Gateway': '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$' # unsafe match
    }, 
    'Wireless': {
        'SSID': '',
        'Passphrase': '',
        'DHCP': '^(1|0)$',
        'IP': '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', # unsafe match
        'Subnet': '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', # unsafe match
        'Gateway': '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$' # unsafe match
    }, 
    'Locale': {
        'Locale': '', # unsafe match
        'DefaultLocale': '', # unsafe match
        'KeyboardModel': '', # unsafe match
        'KeyboardLayout': '', # unsafe match
        'Timezone': '' # unsafe match
    },
    'APT': {
        # RFC1738. rough match
        'Mirror': '^(https|http|ftp)://[0-9a-zA-Z$\\-_.+!*\'(),/%]+$' 
    }, 
    'Remote': {
        'SSH': '^(1|0)$',
        'VNC': '^(1|0)$',
        'VNCPassword': '',
        'VNCResolution': '^((\\d+)x(\\d+))$'
    }, 
    'SimpChinese': {
        'WQYFont': '^(1|0)$',
        'SCIMPinyin': '^(1|0)$',
        'SCIMWubi': '^(1|0)$'
    }
}

############################################################
########## A U X I L I A R Y   F U N C T I O N S  ##########
############################################################

# System requirements check
def envreq():
    # Python 3.1 required
    if sys.hexversion < 0x03010000:
        sys.stderr.write('Python 3.1 or later version required. ' + 
            '(Current version: ' + platform.python_version() + ') \n')
        return False
    
    # OS, architecture and distribution check. Require:
    # * Linux operating system
    # * armv6l hardware architecture
    # * Debian 7.0 "wheezy" distribution
    import platform
    if platform.system() != 'Linux':
        sys.stderr.write('This program must be run under Linux. \n')
        return False
    if not platform.machine().startswith('armv6'):
        sys.stderr.write('This program must be run under an ARMv6 ' + \
            'architecture machine. \n')
        return False
    [linux_dist, linux_ver, linux_id] = platform.linux_distribution()
    if linux_dist.lower() != 'debian' or not (linux_ver.startswith('7') or \
        linux_ver.find('wheezy') != -1):
        sys.stderr.write('This program must be run under Debian ' + \
            'GNU/Linux 7.0/wheezy. \n')
        return False
    
    # Root required
    import os
    if not os.geteuid() == 0:
        sys.stderr.write('This program must be run as root. \n')
        return False
    
    # All requirements OK
    return True
# end of envreq()

# Config file load
def loadconfig(filename='/boot/autoconfig.ini'):
    import configparser;
    configfile = configparser.ConfigParser()
    readret = configfile.read(filename)
    if len(readret) == 0:
        sys.stderr.write('Unable to load configuration file \"' + filename + \
            '\". \n')
        return False
    return configfile
# end of loadconfig()

# Find one network card, from a list of ethernet cards like:
#  [('eth0', 'b8:27:eb:00:00:00'), ('eth1', 'aa:bb:cc:dd:ee:ff')]
# Sequence:
#  (1) MAC address starts with B8:27:EB.
#      Note: B8-27-EB = Raspberry Pi Foundation. 
#  (2) eth0. 
#  (3) If none of above matches, first one. 
def choose_eth(ethslist):
    if not ethslist: return # no return value for []. 
    # (1) MAC address. 
    for eth in ethslist: 
        if eth[1].lower().startswith('b8:27:eb'):
            return eth
    # (2) eth0. 
    for eth in ethslist: 
        if eth[0].lower() ==  'eth0':
            return eth
    # (3) first one.
    return ethslist[0]
# end of choose_eth()

# Find the proper block for specific device in /etc/network/interfaces file, 
#  and change/insert dhcp and static IP settings lines into it. 
# Parameters:
#  interflist: a list of each line in /etc/network/interfaces.
#  devname: device name (eth*, wlan0 etc)
#  datadict: a dictionary of settings. supported:
#   'dhcp': DHCP enabled, True or False, REQUIRED
#   'ip': IP address
#   'subnet': Subnet mask
#   'gateway': Default gateway
def dhcp_and_ip_setting(interflist, devname, datadict):
    import re
    # Find editing range
    #  Find "iface <devname> inet (static|dhcp|manual)" line
    startline = -1
    patt = 'iface\\s+' + devname + '\\s+inet\\s+(?:dhcp|static|manual)'
    for i in range(len(interflist)):
        if re.match(patt, interflist[i]):
            startline = i;
            break
    if (startline == -1): # not found - append to file
        startline = len(interflist)
        interflist.append('')
    #  Find next other device name appeared from startline
    endline = -1
    patt = '\\b(?:eth\\d+|wlan\\d+|lo)\\b'
    pattexcl = '\\b' + devname + '\\b'
    for i in range(startline + 1, len(interflist)):
        if re.search(patt, interflist[i]) and not \
            re.search(pattexcl, interflist[i]):
            endline = i - 1
            break
    if (endline == -1): # not found - edit to eof
        endline = len(interflist) - 1
    #  Create a copy of editing range
    editrange = interflist[startline : endline+1]
    
    # DHCP & IP address
    if 'dhcp' in datadict:
        if datadict['dhcp'] == True:
            # 1st line, DHCP Enabled/Disabled
            editrange[0] = 'iface ' + devname + ' inet dhcp'
            # Strip all address/netmask/gateway lines
            pattexcl = '\\b(?:address|netmask|gateway)\\b'
            pattincl = '^\s*#' # preserve comment lines
            editrange = [l for l in editrange if not re.search(pattexcl, l) \
                or re.match(pattincl, l)]
        else:
            # 1st line, DHCP Enabled/Disabled
            editrange[0] = 'iface ' + devname + ' inet static'
            # Strip all existing address/netmask/gateway lines
            pattexcl = '\\b(?:address|netmask|gateway)\\b'
            pattincl = '^\s*#' # preserve comment lines
            editrange = [l for l in editrange if not re.search(pattexcl, l) \
                or re.match(pattincl, l)]
            # Insert new address/netmask/gateway lines
            if 'ip' in datadict and 'subnet' in datadict and \
                'gateway' in datadict:
                editrange.insert(1, ' address ' + str(datadict['ip']))
                editrange.insert(2, ' netmask ' + str(datadict['subnet']))
                editrange.insert(3, ' gateway ' + str(datadict['gateway']))
    # Restore editing range copy into original list
    interflist[startline : endline+1] = editrange
    return interflist
# end of dhcp_and_ip_setting()

# Edit locales to be generated, and default locale.
def localization_locales(locales_togenerate=[], defaultlocale=None):
    # Load all supported locales of the system first. 
    try:
        locales_supported = open('/usr/share/i18n/SUPPORTED', 'r').read() \
            .split('\n')
        if '' in locales_supported: locales_supported.remove('')
    except:
        sys.stderr.write('FAILED: Unable to get supported locales of ' + \
            'system! \n')
        sys.stderr.write('FAILED: All locales settings unchanged. \n')
        return
    return
    
    # Edit locales, completely rewrite `/etc/locale.gen`
    #  (list all supported locales, add leading # before ungenerated ones)
    if locales_togenerate:
        try:
            flocalesgen = open("/home/pi/locale.txt", 'w')
            flocalesgen.write('''\
# This file lists locales that you wish to have built. You can find a list
# of valid supported locales at /usr/share/i18n/SUPPORTED, and you can add
# user defined locales to /usr/local/share/i18n/SUPPORTED. If you change
# this file, you need to rerun locale-gen.
#

'''
            for locale in locales_supported:
                if not locale in locale_to_generate: 
                    flocalesgen.write('# ')
                flocalesgen.write(locale + '\n');
            flocalesgen.close()
        except IOError:
            sys.stderr.write('FAILED: Unable to write /etc/locale.gen! \n')
            sys.stderr.write('FAILED: Locales unchanged. \n')
    
    # Edit default locale, write `/etc/default/locale`
    if defaultlocale:
        try:
            if defaultlocale in locales_supported:
                fdefaultlocale = open("/home/pi/deflocale.txt", 'w')
                fdefaultlocale.write('LANG=' + defaultlocale);
                flocalesgen.close()
            else:
                sys.stderr.write('FAILED: ' + defaultlocale + ' is not a ' + \
                    'a valid locale! \n')
                sys.stderr.write('FAILED: Default locale unchanged. \n')
        except IOError:
            sys.stderr.write('FAILED: Unable to write /etc/default/locale! \n')
            sys.stderr.write('FAILED: Default locale unchanged. \n')
    
    # Run dpkg-reconfigure
    if locales_togenerate or defaultlocale:
        import subprocess
        subprocess.call(['dpkg-reconfigure', '--frontend=noninteractive', 
            'locales'])
    
    return
# end of localization_locales()

############################################################
############# C O N F I G   F U N C T I O N S  #############
############################################################

def setup_screen(configfile):
    SECNAME = 'Screen'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring screen... \n')
    
    reboot = False
    
    # Load config.txt
    try:
        cnftxt = open('/boot/config.txt', 'r').read()
    except IOError:
        cnftxt = ''
    except:
        sys.stderr.write('FAILED: Unable to read or create ' + \
            '/boot/config.txt! \n')
        sys.stderr.write('FAILED: All screen settings unchanged. \n')
        return False
    # Regex lib needed for editing config.txt
    import re
    
    # [Screen].Resolution
    if configfile.has_option(SECNAME, 'Resolution'):
        value = configfile.get(SECNAME, 'Resolution')
        if value.lower() == 'auto':
            # Comments out "hdmi_ignore_edid", "hdmi_group" & "hdmi_mode"
            patt = '^(hdmi_ignore_edid)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            patt = '^(hdmi_group)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            patt = '^(hdmi_mode)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            reboot = True
        else:
            m = re.match('^(?P<hdmigroup>1|2),\\s*(?P<hdmimode>\\d+)$', value)
            if m: # Parsable input (not strictly verified)
                hdmigroup = int(m.group('hdmigroup'))
                hdmimode = int(m.group('hdmimode'))
                # hdmi_mode=1~59 for hdmigroup=1, 1~86 for hdmigroup=2
                if (hdmigroup==1 and hdmimode>=1 and hdmimode<=59) or \
                    (hdmigroup==2 and hdmimode>=1 and hdmimode<=86):
                    # Set hdmi_group=<var:hdmigroup>
                    patt = '^.*hdmi_group.*$'
                    repl = 'hdmi_group=' + str(hdmigroup)
                    [cnftxt, n] = re.subn(patt, repl, cnftxt, 1, flags=re.M)
                    if n == 0: cnftxt += '\n' + repl
                    # Set hdmi_mode=<var:hdmimode>
                    patt = '^.*hdmi_mode.*$'
                    repl = 'hdmi_mode=' + str(hdmimode)
                    [cnftxt, n] = re.subn(patt, repl, cnftxt, 1, flags=re.M)
                    if n == 0: cnftxt += '\n' + repl
                    # Set hdmi_ignore_edid=0xa5000080
                    patt = '^.*hdmi_ignore_edid.*$'
                    repl = 'hdmi_ignore_edid=0xa5000080'
                    [cnftxt, n] = re.subn(patt, repl, cnftxt, 1, flags=re.M)
                    if n == 0: cnftxt += '\n' + repl
                    reboot = True
                else: # hdmi_mode value out of range
                    sys.stderr.write('WARN: HDMI_Mode value specified in ' + \
                        '[Screen].Output out of range. \n')
                    sys.stderr.write('FAILED: Resolution unchanged. \n')
            else: # Any other invalid value
                sys.stderr.write('WARN: Invalid [Screen].Resolution value. \n')
                sys.stderr.write('FAILED: Resolution unchanged. \n')
    # end of [Screen].Resolution
    
    # [Screen].Output
    if configfile.has_option(SECNAME, 'Output'):
        value = configfile.get(SECNAME, 'Output')
        if value.lower() == 'auto':
            # Comment out "hdmi_force_hotplug" & "hdmi_ignore_hotplug"
            patt = '^(hdmi_force_hotplug)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            patt = '^(hdmi_ignore_hotplug)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            reboot = True
        elif value.lower() == 'hdmi':
            # Set "hdmi_force_hotplug=1", comment out "hdmi_ignore_hotplug"
            patt = '^.*hdmi_force_hotplug.*$'
            repl = 'hdmi_force_hotplug=1'
            [cnftxt, n] = re.subn(patt, repl, cnftxt, 1, flags=re.M)
            if n == 0: cnftxt += '\n' + repl
            patt = '^(hdmi_ignore_hotplug)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            reboot = True
        elif value.lower() == 'comp':
            # Comment out "hdmi_force_hotplug", set "hdmi_ignore_hotplug=1"
            patt = '^(hdmi_force_hotplug)'; repl = '#\g<0>'
            cnftxt = re.sub(patt, repl, cnftxt, flags=re.M)
            patt = '^.*hdmi_ignore_hotplug.*$'
            repl = 'hdmi_ignore_hotplug=1'
            [cnftxt, n] = re.subn(patt, repl, cnftxt, 1, flags=re.M)
            if n == 0: cnftxt += '\n' + repl
            reboot = True
        else: # Any other invalid value
            sys.stderr.write('WARN: Invalid [Screen].Output value. \n')
            sys.stderr.write('FAILED: Output device unchanged. \n')
    # end of[Screen].Output
    
    # Write back config.txt
    open('/boot/config.txt', 'w').write(cnftxt)
    
    sys.stdout.write('INFO: Screen config complete. \n')
    return reboot
# end of setup_screen()

def setup_wired(configfile):
    SECNAME = 'Wired'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring wired network... \n')
    
    # Load /etc/network/interfaces
    try:
        interf = open('/etc/network/interfaces', 'r').read().split('\n')
    except:
        sys.stderr.write('FAILED: Unable to read /etc/network/interfaces! \n')
        sys.stderr.write('FAILED: All wired network settings unchanged. \n')
        return False
    # Regex lib needed for editing text file
    import re
    
    # Show all wired ethernet network cards (eth*)
    # Fetch `ip link show` command stdout
    import subprocess
    ipoutput = subprocess.check_output(['ip', 'link', 'show'],
        universal_newlines=True)
    # Find device name (eth*) and mac address from output
    import re
    patt = '^\d+:\s(?P<dev>eth\d+).*\n' + \
        '\s*link/ether\s+(?P<hwaddr>(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})'
    eths = re.findall(patt, ipoutput, flags=re.M) 
    # eg: [('eth0', 'b8:27:eb:00:00:00'), ('eth1', 'aa:bb:cc:dd:ee:ff')]
    
    # Count NIC, get device name and MAC address. 
    if len(eths) == 1: 
        # One NIC (most probably Model B integrated one), use it directly.
        (ethdev, ethmac) = eths[0]
    elif len(eths) > 1:
        # Multi NIC
        sys.stderr.write('WARN: ' + str(len(eths)) + \
            ' ethernet devices (eth*) found. \n')
        (ethdev, ethmac) = choose_eth(eths)
        sys.stderr.write('INFO: Configuring ' + ethdev + \
            ' (' + ethmac + '). \n')
    else:
        # No NIC
        sys.stderr.write('WARN: No ethernet device (eth*) found! \n')
        sys.stderr.write('FAILED: All wired network settings unchanged. \n')
        return False
    
    # [Wired].DHCP, and [Wired].IP/Subnet/Gateway (if DHCP=0)
    if configfile.has_option(SECNAME, 'DHCP'):
        value = configfile.get(SECNAME, 'DHCP')
        if value == '1':
            interf = dhcp_and_ip_setting(interf, ethdev, {'dhcp': True})
        elif value == '0':
            sdict = {'dhcp': False}
            sdict['ip'] = configfile.get(SECNAME, 'IP')
            sdict['subnet'] = configfile.get(SECNAME, 'Subnet')
            sdict['gateway'] = configfile.get(SECNAME, 'Gateway')
            interf = dhcp_and_ip_setting(interf, ethdev, sdict)
        else:
            sys.stderr.write('WARN: Invalid [Wired].DHCP value. \n')
            sys.stderr.write('FAILED: DHCP for ' + ethdev + ' unchanged. \n')
    
    # Write back changes to /etc/network/interfaces
    open('/etc/network/interfaces', 'w').write('\n'.join(interf)) 
    
    # Down and up (reset) ethernet device
    subprocess.call(['ifdown', ethdev])
    subprocess.call(['ifup', ethdev])
    
    sys.stdout.write('INFO: Wired network config complete. \n')
    return True
# end of setup_wired

def setup_wireless(configfile):
    SECNAME = 'Wireless'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring wireless network... \n')
    
    # Requires [Wireless].SSID option. 
    if configfile.has_option(SECNAME, 'SSID'):
        ssid = configfile.get(SECNAME, 'SSID');
    else:
        sys.stderr.write('WARN: SSID option required for configuring ' + \
            'wireless network! \n')
        sys.stderr.write('FAILED: All wireless network settings unchanged. \n')
        return False
    
    # Show all wireless ethernet network cards (eth*)
    # Fetch `iwconfig` command stdout
    import subprocess
    ipoutput = subprocess.check_output(['iwconfig'], universal_newlines=True, \
        stderr=open('/dev/null', 'w'))
    # Find device name (wlan*) from output
    import re
    patt = '^(?P<dev>\\w+)\\s+IEEE\s*802\\.11'
    eths = re.findall(patt, ipoutput, flags=re.M) # eg: ['wlan0', 'wlan1']
    
    # Count NIC, get device name. 
    if len(eths) == 1: 
        # One NIC, use it directly.
        ethdev = eths[0]
    elif len(eths) > 1:
        # Multi NIC, wlan0 preferred
        sys.stderr.write('WARN: ' + str(len(eths)) + \
            ' Wi-Fi devices found. \n')
        if 'wlan0' in eths:
            ethdev = 'wlan0'
        else:
            ethdev = eths[0]
        sys.stderr.write('INFO: Configuring ' + ethdev + \
            ' (' + ethmac + '). \n')
    else:
        # No NIC
        sys.stderr.write('WARN: No Wi-Fi device found! \n')
        sys.stderr.write('FAILED: All wireless network settings unchanged. \n')
        return False
    
    # Scan networks
    subprocess.call(['iwlist', ethdev, 'scan'], stdout=open('/dev/null', 'w'))
    aplist = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
        'scan_results'], universal_newlines=True).split('\n')
    #  strip leading head line and trailing newline
    aplist.remove(aplist[0])
    if '' in aplist: aplist.remove('')
    #  explode each line by tab char
    #  (Note: column title: bssid, frequency, signal level, flags, ssid)
    aplist = [ap.split('\t') for ap in aplist]
    #  find record with specific ssid
    apinfo = list(filter(lambda ap: len(ap)==5 and ap[4]==ssid, aplist))
    if not apinfo: # AP Not found in current area
        sys.stderr.write('ERROR: Access point \"' + ssid + '\" not found! \n')
        sys.stderr.write('FAILED: All wireless network settings unchanged. \n')
        return False
    #  analyze encryption method
    if 'wpa' in apinfo[0][3].lower(): # WPA/WPA2 Encryption
        encryptmethod = 'wpa'
    elif 'wep' in apinfo[0][3].lower(): # WEP Encryption
        encryptmethod = 'wep'
    else:
        encryptmethod = 'none'
    
    # Configure wireless network with wpa_cli
    cliOK = {};
    #  config data check: must exists [Wireless].Paraphrase for any encryption
    if not encryptmethod == 'none':
        if not configfile.has_option(SECNAME, 'Passphrase'):
            sys.stderr.write('ERROR: No passphrase provided for ' + \
                ' WPA/WPA2 encrypted access point \"' + ssid + '\"! \n')
            sys.stderr.write('FAILED: All wireless network settings unchanged. \n')
            return False
        else:
            passphrase = configfile.get(SECNAME, 'Passphrase');
    #  create network in wpa_cli
    netid = subprocess.check_output(['wpa_cli', '-i'+ethdev, 'add_network'], 
        universal_newlines=True)
    #  set ssid
    cliOK['ssid'] = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
        'set_network', netid, 'ssid', '\"' + ssid + '\"'], 
        universal_newlines=True)
    # cliOK['scan_ssid'] = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
        # 'set_network', netid, 'scan_ssid', '1'], universal_newlines=True)
    #  set wpa/wpa2/wep encryption
    if 'wpa' in apinfo[0][3].lower(): # WPA/WPA2 Encryption
        # only wpa-psk supported in current version
        cliOK['key_mgmt'] = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
            'set_network', netid, 'key_mgmt', 'WPA-PSK'], 
             universal_newlines=True)
        cliOK['psk'] = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
            'set_network', netid, 'psk', '"' + passphrase + '"'], 
             universal_newlines=True)
    elif 'wep' in apinfo[0][3].lower(): # WEP Encryption
        cliOK['key_mgmt'] = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
            'set_network', netid, 'key_mgmt', 'NONE'], 
             universal_newlines=True)
        for i in range(4):
            cliOK['wep_key'+str(i)] = subprocess.check_output(['wpa_cli', 
                '-i'+ethdev, 'set_network', netid, 'wep_key'+str(i), 
                '' + passphrase + ''], universal_newlines=True)
    else: # Open, no encryption
        pass
    
    # Enable network (connect to it automatically)
    cliOK['enable_network'] = subprocess.check_output(['wpa_cli', '-i'+ethdev, 
        'enable_network', netid], universal_newlines=True)
    
    # Save config for next boot up - don't forget this!
    subprocess.call(['wpa_cli', '-i'+ethdev, 'save_config'], 
        stdout=open('/dev/null', 'w'))
    
    sys.stdout.write('INFO: Wireless network config complete. \n')
    return False
# end of setup_wireless

def setup_localization(configfile):
    SECNAME = 'Localization'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring localization settings... \n')
    
    # Regex lib needed for editing text file
    import re
    
    # Edit locales and default locale
    if configfile.has_option(SECNAME, 'Locales') or \
        configfile.has_option(SECNAME, 'DefaultLocale'):
        if configfile.has_option(SECNAME, 'Locales'):
            localeslist = configfile.get(SECNAME, 'Locales').split(',')
            localeslist = list(map(lambda s: s.strip(), localeslist))
        else:
            localeslist = []
        if configfile.has_option(SECNAME, 'DefaultLocale'):
            defaultlocale = configfile.get(SECNAME, 'DefaultLocale')
        else:
            defaultlocale = ''
        localization_locales(localeslist, defaultlocale)
    
    # Edit keyboard model and layout 
    pass
    
    # Edit timezone
    pass
    
    sys.stdout.write('INFO: Localization config complete. \n')
    return True
# end of setup_localization

############################################################
################ M A I N   R O U T L I N E  ################
############################################################

def main(argv):
    # System requirements check
    if not envreq():
        sys.stderr.write('ERROR: System requirements are not satisfied! \n')
        return 1
    
    # Load config file
    # `/boot/autoconfig.ini` for default,
    # but can also be customized via command line.
    if (len(sys.argv) < 2):
        configfile = loadconfig()
    else:
        configfile = loadconfig(sys.argv[1])
    
    if not configfile:
        sys.stderr.write('ERROR: autoconfig.ini file read error. \n')
        return 1
    
    sys.stdout.write(RPAC_SPLASH_STRING)
    
    # Config routline
    reboot = False
    reboot = reboot or setup_screen(configfile)
    reboot = reboot or setup_wired(configfile)
    reboot = reboot or setup_wireless(configfile)
    reboot = reboot or setup_localization(configfile)
    
    # Normal Exit
    sys.stdout.write('All configuration completed. \n')
    return 0
# end of main()

if __name__ == '__main__': # Must be run standalone
    sys.exit(main(sys.argv))
