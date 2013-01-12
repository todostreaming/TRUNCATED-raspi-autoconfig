#! /usr/bin/env python3

# raspi-autoconfig 1.0.2
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

# Available sections
RPAC_SECTIONS = ['System', 'Screen', 'Wired', 'Wireless', 'Localization', 
    'APT', 'Remote', 'SimpChinese']

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
def loadconfig(filename):
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

''')
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

# Edit keyboard model and/or layout. 
def localization_keyboard(model=None, layout=None):
    # Load /etc/default/keyboard
    try:
        kbconffile = open('/etc/default/keyboard', 'r').read()
    except:
        sys.stderr.write('FAILED: Unable to read keyboard configuration ' + \
            'file /etc/default/keyboard! \n')
        sys.stderr.write('FAILED: All keyboard settings unchanged. \n')
        return
    
    # Regex for editing text
    import re
    
    # Keyboard model
    if model:
        patt = '^XKBMODEL\\s*=\\s*"(?P<modelname>.+)"'
        repl = 'XKBMODEL=\"' + re.escape(model) + '\"'
        [kbconffile, n] = re.subn(patt, repl, kbconffile, 1, flags=re.M)
        if n == 0: kbconffile += '\n' + repl
    
    # Keyboard layout
    if layout:
        patt = '^XKBLAYOUT\\s*=\\s*"(?P<layoutname>.+)"'
        repl = 'XKBLAYOUT=\"' + re.escape(layout) + '\"'
        [kbconffile, n] = re.subn(patt, repl, kbconffile, 1, flags=re.M)
        if n == 0: kbconffile += '\n' + repl
    
    # Write back to /etc/default/keyboard
    try:
        open('/etc/default/keyboard', 'w').write(kbconffile)
    except:
        sys.stderr.write('FAILED: Unable to write keyboard configuration ' + \
            'file /etc/default/keyboard! \n')
        sys.stderr.write('FAILED: All keyboard settings unchanged. \n')
        return
    
    # Run dpkg-reconfigure and invoke-rc.d
    import subprocess
    subprocess.call(['dpkg-reconfigure', '--frontend=noninteractive', 
        'keyboard-configuration'])
    subprocess.call(['invoke-rc.d', 'keyboard-setup', 'start'])
    
    return
# end of localization_keyboard()

# Edit timezone. 
def localization_timezone(timezone):
    if not timezone: return
    
    # Write timezone to /etc/timezone
    try:
        open('/etc/timezone', 'w').write(timezone)
    except:
        sys.stderr.write('FAILED: Unable to write timezone configuration ' + \
            'file /etc/timezone! \n')
        sys.stderr.write('FAILED: Timezone unchanged. \n')
        return
    
    # Run dpkg-reconfigure
    import subprocess
    subprocess.call(['dpkg-reconfigure', '--frontend=noninteractive', 
        'tzdata'])
    
    return
# end of localization_timezone()

# Edit APT mirror. 
def apt_mirror(mirrorurl):
    # URL Verification (1.in right format; 2.reachable)
    import re, urllib.request, socket
    mirrorurl = mirrorurl.strip()
    patt = '^(https|http|ftp)://[0-9a-zA-Z$\\\\-_.+!*\\\'(),/%]+$'
    if not re.match(patt, mirrorurl, re.M):
        sys.stderr.write('FAILED: ' + mirrorurl + ' is not a valid HTTP/' + \
            'HTTPS/FTP URL! \n')
        sys.stderr.write('FAILED: APT mirror unchanged. \n')
        return
    print("Connecting to "  + mirrorurl + "...")
    try:
        resp = urllib.request.urlopen(mirrorurl, timeout=15)
    except (urllib.error.URLError, socket.error) as err:
        sys.stderr.write('FAILED: Unable to reach ' + mirrorurl + ' ! \n')
        sys.stderr.write('(Check your network connection and mirror URL). \n')
        sys.stderr.write('FAILED: APT mirror unchanged. \n')
        return
    
    # Read /etc/apt/sources.list
    try:
        aptlist = open('/etc/apt/sources.list', 'r').read().split('\n')
        aptlist = list(map(lambda s: s.strip(), aptlist))
    except:
        sys.stderr.write('FAILED: Unable to read APT source list file ' + \
            '/etc/apt/sources.list! \n')
        sys.stderr.write('FAILED: APT mirror unchanged. \n')
        return
    
    # Comment out every uncommented line
    for i, aptline in enumerate(aptlist):
        if aptline and aptline[0] != '#':
            aptlist[i] = '# ' + aptline
    
    aptlist.append('deb ' + mirrorurl + ' wheezy main contrib non-free rpi')
    
    # Write back to /etc/apt/sources.list
    try:
        open('/etc/apt/sources.list', 'w').write('\n'.join(aptlist))
    except:
        sys.stderr.write('FAILED: Unable to write APT source list file ' + \
            '/etc/apt/sources.list! \n')
        sys.stderr.write('FAILED: APT mirror unchanged. \n')
        return
    
    # Run apt-get update
    import subprocess
    subprocess.call(['apt-get', 'update'])
    
    return
# end of apt_mirror()

# Install vnc server autorun script. 
def remote_vnc_autorun_install(resolutionwidth=800, resolutionheight=600):
    # exception handling pending for this function!!!
    
    SCRIPTCONTENT = '''\
#!/bin/sh
### BEGIN INIT INFO
# Provides:          tightvncserver
# Required-Start:    $local_fs
# Required-Stop:     $local_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start/stop tightvncserver
### END INIT INFO

# More details see:
# http://www.penguintutor.com/linux/tightvnc

### Customize this entry
# Set the USER variable to the name of the user to start tightvncserver under
export USER='pi'
### End customization required

eval cd ~$USER

case "$1" in
  start)
    su $USER -c '/usr/bin/tightvncserver -geometry ''' + \
str(resolutionwidth) + 'x' + str(resolutionheight) + \
''' :1'
    echo "Starting TightVNC server for $USER "
    ;;
  stop)
    su $USER -c '/usr/bin/tightvncserver -kill :1'
    echo "Tightvncserver stopped"
    ;;
  *)
    echo "Usage: /etc/init.d/tightvncserver {start|stop}"
    exit 1
    ;;
esac
exit 0
'''
    SCRIPTPATH = '/etc/init.d/'
    SCRIPTFILENAME = 'tightvncserver'
    import os
    SCRIPTFULLPATH = os.path.join(SCRIPTPATH, SCRIPTFILENAME)
    
    # Write script file in /etc/init.d/
    open(SCRIPTFULLPATH, 'w').write(SCRIPTCONTENT)
    # Chmod +x
    import os, stat
    filestat = os.stat(SCRIPTFULLPATH)
    os.chmod(SCRIPTFULLPATH, filestat.st_mode | stat.S_IEXEC)
    # Run update-rc.d
    import subprocess
    subprocess.call(['update-rc.d', SCRIPTFILENAME, 'defaults'])
    
    return
# end of remote_vnc_autorun_install()

# Uninstall vnc server autorun script. 
def remote_vnc_autorun_uninst():
    search_path = '/etc/init.d/'
    # Find all scripts including 'vncserver' and delete them
    import os
    filelist = os.listdir(search_path)
    for filename in filelist:
        full_path = os.path.join(search_path, filename)
        if not os.path.isfile(full_path):
            continue;
        filecontent = open(full_path, 'r').read()
        if 'vncserver' in filecontent:
            os.remove(full_path)
# end of remote_vnc_autorun_uninst()

############################################################
############# C O N F I G   F U N C T I O N S  #############
############################################################

def setup_system(configfile):
    SECNAME = 'System'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring system... \n')
    
    reboot = False
    if configfile.has_option(SECNAME, 'ExpandRootfs'):
        Expandrootfs = configfile.get(SECNAME, 'ExpandRootfs').strip()
        if Expandrootfs == '1':
            import subprocess
            # Get start sector of /dev/mmcblk0p2
            sys.stdout.write('Expand root filesystem to fill the SD card' + \
                '... \n')
            ptable = subprocess.check_output(['fdisk', '-l', '/dev/mmcblk0'], 
                universal_newlines=True)
            precord = (ptable.split('\n')[-2]).split()
            pstartsector = precord[1]
            # Launch fdisk
            fdisk_stdin = bytes('p\nd\n2\nn\np\n2\n' + pstartsector + \
                '\n\np\nw\n', 'ascii')
            fdisk_proc = subprocess.Popen(['fdisk', '/dev/mmcblk0'], 
                stdin=subprocess.PIPE)
            fdisk_proc.communicate(fdisk_stdin)
            reboot = True
        elif Expandrootfs == '0':
            pass
        else:
            sys.stderr.write('WARN: Only 1 for option [System].' + \
                'Expandrootfs please. \n')
            sys.stderr.write('WARN: Root filesystem not expanded. \n')
    
    if configfile.has_option(SECNAME, 'BootBehavior'):
        BootBehavior = configfile.get(SECNAME, 'BootBehavior').strip().lower()
        import subprocess
        if BootBehavior == 'commandlinelogin':
            subprocess.call(['update-rc.d', 'lightdm', 'disable', '2'])
            reboot = True
        elif BootBehavior == 'desktopauto':
            subprocess.call(['update-rc.d', 'lightdm', 'enable', '2'])
            # Edit /etc/lightdm/lightdm.conf
            import re
            cnftxt = open('/etc/lightdm/lightdm.conf', 'r').read()
            patt = '^(?P<confline>\s*#\s*autologin-user=.*)$'
            repl = 'autologin-user=pi'
            [cnftxt, n] = re.subn(patt, repl, cnftxt, 1, flags=re.M)
            if n == 0: cnftxt += '\n' + repl
            open('/etc/lightdm/lightdm.conf', 'w').write(cnftxt)
            reboot = True
        else:
            sys.stderr.write('WARN: Invalid value for [System].' + \
                'BootBehavior. \n')
            sys.stderr.write('WARN: Boot behavior unchanged. \n')
    
    sys.stdout.write('INFO: System config complete. \n')
    return reboot
# end of setup_system()

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
    return False
# end of setup_wired()

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
# end of setup_wireless()

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
    if configfile.has_option(SECNAME, 'KeyboardModel') or \
        configfile.has_option(SECNAME, 'KeyboardLayout'):
        model = configfile.get(SECNAME, 'KeyboardModel', fallback=None)
        layout = configfile.get(SECNAME, 'KeyboardLayout', fallback=None)
        localization_keyboard(model, layout)
    
    # Edit timezone
    if configfile.has_option(SECNAME, 'TimeZone'):
        localization_timezone(configfile.get(SECNAME, 'TimeZone'))
    
    sys.stdout.write('INFO: Localization config complete. \n')
    return False
# end of setup_localization()

def setup_apt(configfile):
    SECNAME = 'APT'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring APT settings... \n')
    
    # Edit APT mirror
    if configfile.has_option(SECNAME, 'Mirror'):
        apt_mirror(configfile.get(SECNAME, 'Mirror'))
    
    sys.stdout.write('INFO: APT config complete. \n')
    return False
# end of setup_apt()

def setup_remote(configfile):
    SECNAME = 'Remote'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring remote access settings... \n')
    
    # Required during ssh and vnc setup
    import subprocess
    
    # SSH
    if configfile.has_option(SECNAME, 'SSH'):
        sys.stdout.write('Setting up SSH... \n')
        SSHonoff = configfile.get(SECNAME, 'SSH').strip()
        if SSHonoff == '1':
            subprocess.call(['update-rc.d', 'ssh', 'enable'])
            subprocess.call(['invoke-rc.d', 'ssh', 'start'])
        elif SSHonoff == '0':
            subprocess.call(['update-rc.d', 'ssh', 'disable'])
        else:
            sys.stderr.write('WARN: Only 1 or 0 for option [Remote].SSH ' + \
                'please. \n')
            sys.stderr.write('WARN: SSH settings unchanged. \n')
    
    # VNC
    if configfile.has_option(SECNAME, 'VNC'):
        sys.stdout.write('Setting up VNC... \n')
        VNConoff = configfile.get(SECNAME, 'VNC').strip()
        if VNConoff == '1':
            # [Remote].VNCPassword required on installing VNC
            if configfile.has_option(SECNAME, 'VNCPassword'):
                # Install tightvncserver via APT
                aptret = subprocess.call(['apt-get', '-y', 'install', 
                    'tightvncserver'])
                if aptret == 0:
                    # Set VNC Password via vncpasswd command
                    vncpasswd_unencry = configfile.get(SECNAME, 'VNCPassword')
                    vncpasswd_proc = subprocess.Popen(['vncpasswd', '-f'], 
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    vncpasswd_encry = vncpasswd_proc.communicate(bytes(
                        vncpasswd_unencry, 'ascii'))[0]
                    vncpasswd_proc = None
                    import os.path
                    vncpasswd_filepath = os.path.join(os.path.expanduser(
                        '~pi'), '.vnc/passwd')
                    open(vncpasswd_filepath, 'wb').write(vncpasswd_encry)
                    # Read VNC Resolution
                    vnc_resolution = [None, None]
                    if configfile.has_option(SECNAME, 'VNCResolution'):
                        import re
                        vnc_resolution_raw = configfile.get(SECNAME, 
                            'VNCResolution')
                        patt = '^\\s*(?P<width>\\d+)\\s*' + \
                            'x\\s*(?P<height>\\d+)\\s*$'
                        m = re.match(patt, vnc_resolution_raw)
                        if m:
                            vnc_resolution = [int(m.group('width')), 
                                int(m.group('height'))]
                        else:
                            sys.stderr.write('WARN: [Remote].VNCResolution' + \
                                'value is in wrong format. \n' + \
                                '(Default resolution is used instead.) \n')
                    # Setup VNC autorun
                    remote_vnc_autorun_install(vnc_resolution[0], 
                        vnc_resolution[1])
                    # Start up VNC server
                    subprocess.call(['/etc/init.d/tightvncserver', 'start'])
                else:
                    sys.stderr.write('ERROR: Error occured on installing ' + \
                        'tightvncserver via apt-get!. \n')
                    sys.stderr.write('FAILED: VNC server is not installed. \n')
            else:
                sys.stderr.write('ERROR: A VNC password is required to ' + \
                    'install VNC server! \n' + \
                    '(Please specify a [Remote].VNCPassword value.) \n')
                sys.stderr.write('FAILED: VNC server is not installed. \n')
        elif VNConoff == '0':
            subprocess.call(['apt-get', '-y', 'remove', 'tightvncserver'])
            remote_vnc_autorun_uninst()
        else:
            sys.stderr.write('WARN: Only 1 or 0 for option [Remote].VNC ' + \
                'please. \n')
            sys.stderr.write('WARN: VNC server is not changed. \n')
    
    sys.stdout.write('INFO: Remote access config complete. \n')
    return False
# end of setup_remote()

def setup_simpchinese(configfile):
    SECNAME = 'SimpChinese'
    # Run only if proper section exists in autoconfig.ini
    if not configfile.has_section(SECNAME): return False
    sys.stdout.write('INFO: Configuring Simplified Chinese localization ' + \
        ' settings... \n')
    
    # Required for using apt-get
    import subprocess
    
    # Wenquanyi Font
    if configfile.has_option(SECNAME, 'WQYFont'):
        sys.stdout.write('Installing Wenquanyi Chinese font... \n')
        WQYinst = configfile.get(SECNAME, 'WQYFont').strip()
        if WQYinst == '1':
            subprocess.call(['apt-get', '-y', 'install', 'ttf-wqy-zenhei'])
        else:
            sys.stderr.write('WARN: Only 1 for option [SimpChinese].' + \
                'WQYFont please. \n')
            sys.stderr.write('WARN: Wenquanyi Chinese font not installed. \n')
    
    # SCIM Pinyin/Wubi
    if configfile.has_option(SECNAME, 'SCIMPinyin') or \
        configfile.has_option(SECNAME, 'SCIMWubi'):
        SCIMPinyin_inst = configfile.get(SECNAME, 'SCIMPinyin').strip()
        SCIMWubi_inst = configfile.get(SECNAME, 'SCIMWubi').strip()
        sys.stdout.write('Installing SCIM Chinese input method... \n')
        if SCIMPinyin_inst == '1':
            subprocess.call(['apt-get', '-y', 'install', 'scim', 
                'scim-pinyin'])
        else:
            sys.stderr.write('WARN: Only 1 for option [SimpChinese].' + \
                'SCIMPinyin please. \n')
            sys.stderr.write('WARN: SCIM(Pinyin) not installed. \n')
        if SCIMWubi_inst == '1':
            subprocess.call(['apt-get', '-y', 'install', 'scim', 
                'scim-tables-zh'])
        else:
            sys.stderr.write('WARN: Only 1 for option [SimpChinese].' + \
                'SCIMWubi please. \n')
            sys.stderr.write('WARN: SCIM(Wubi) not installed. \n')
    
    sys.stdout.write('INFO: Simplified Chinese localization config ' + \
        'complete. \n')
    return False
# end of setup_simpchinese()

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
        configfilepath = '/boot/autoconfig.ini'
    else:
        configfilepath = sys.argv[1]
    configfile = loadconfig(configfilepath)
    configfiletext = open(configfilepath, 'r').read()
    
    if not configfile:
        sys.stderr.write('ERROR: autoconfig.ini file read error. \n')
        return 1
    
    # Exit if config file empty
    configfileempty = True
    for sectionname in RPAC_SECTIONS:
        if configfile.has_section(sectionname):
            configfileempty = False
            break
    if configfileempty:
        sys.stderr.write('Notice: raspi-autoconfig is not run, because ' + \
            'autoconfig.ini file is empty. \n')
        return 0
    
    # Else, start program
    sys.stdout.write(RPAC_SPLASH_STRING)
    
    # Config routline
    reboot = False
    reboot = reboot or setup_system(configfile)
    reboot = reboot or setup_screen(configfile)
    reboot = reboot or setup_wired(configfile)
    reboot = reboot or setup_wireless(configfile)
    reboot = reboot or setup_localization(configfile)
    reboot = reboot or setup_apt(configfile)
    reboot = reboot or setup_remote(configfile)
    reboot = reboot or setup_simpchinese(configfile)
    
    # Normal Exit
    sys.stdout.write('All configuration completed. \n')
    
    # Truncate autoconfig.ini file (comment out every valid line)
    import re
    patt = '^[^#;\\s]*[a-zA-Z0-9_\\[\\]\\=].*$'
    repl = '#\\g<0>'
    configfiletext = re.sub(patt, repl, configfiletext, flags=re.M)
    #  DOS/Windows newline for Windows compatibility
    open(configfilepath, 'w', newline='\r\n').write(configfiletext)
    
    # Reboot
    if reboot:
        sys.stdout.write('NOTICE: Reboot is needed for some configuration ' + \
            'steps!!! \n')
        sys.stdout.write('SYSTEM IS GOING TO REBOOT IN 5 SECONDS. \n')
        import subprocess
        subprocess.call(['sleep', '5'])
        subprocess.call(['reboot'])
        return 0
    
    return 0
# end of main()

if __name__ == '__main__': # Must be run standalone
    sys.exit(main(sys.argv))
