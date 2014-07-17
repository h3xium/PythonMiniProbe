#!/usr/bin/env python
#Copyright (c) 2014, Paessler AG <support@paessler.com>
#All rights reserved.
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

### Quick and Dirty Setup Script for the Mini Probe
import sys
import os
import time
import subprocess


def file_check(path):
    # Check if a give file exists
    return os.path.exists(path)


def file_create(path):
    # Creates a given file and writes some startup information to it
    with open(path, 'w') as f:
        f.write("###Mini Probe Config File\n")
        f.close()


def write_config(config):
    conf = ""
    with open(path, 'a') as f:
        for key in config:
            conf += "%s:%s\n" % (key, config[key])
        f.write(conf)
    f.close()
    print "Config file successfully written!"


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
    f.close()


def logrotation(path):
    rotatetemplate = """%s/logs/probe.log {
    rotate 4
    daily
    dateext
    compress
    missingok
    }
    """ % path
    return rotatetemplate


def init_script(path, user):
    scripttemplate = """
#!/usr/bin/env sh

### BEGIN INIT INFO
# Provides:          probe.sh
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: will run the MiniProbe as service
# Description:       Put a long description of the service here
### END INIT INFO

# Change the next 3 lines to suit where you install your script and what you want to call it
DIR=%s
DAEMON=$DIR/probe.py
DAEMON_NAME=probe.sh

# This next line determines what user the script runs as.
# Root generally not recommended but necessary if you are using the Raspberry Pi GPIO from Python.
DAEMON_USER=%s

# The process ID of the script when it runs is stored here:
PIDFILE=/var/run/$DAEMON_NAME.pid

. /lib/lsb/init-functions

do_start () {
    log_daemon_msg "Starting system $DAEMON_NAME daemon"
    start-stop-daemon --start --background --pidfile $PIDFILE --make-pidfile --chdir $DIR --user $DAEMON_USER --chuid $DAEMON_USER --startas $DAEMON
    log_end_msg $?
}
do_stop () {
    log_daemon_msg "Stopping system $DAEMON_NAME daemon"
    start-stop-daemon --stop --pidfile $PIDFILE --retry 10
    log_end_msg $?
}

case "$1" in

    start|stop)
        do_${1}
        ;;

    restart|reload|force-reload)
        do_stop
        do_start
        ;;

    status)
        status_of_proc "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
        ;;
    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|restart|status}"
        exit 1
        ;;

esac
exit 0
""" % (path, user)
    return scripttemplate

if __name__ == '__main__':
    conf_avail = False
    print"""
Welcome to the Miniprobe (Python) for PRTG installer
    """
    print """
Checking for necessary modules and Python Version
    """
    print "."
    try:
        sys.path.append('./')
        import hashlib
        import string
        import json
        import socket
        import importlib
        import requests
        import pyasn1
        import pysnmp
    except Exception, e:
        print "%s.Please install the same" % e
        print "Exiting"
        sys.exit(1)
    time.sleep(1)
    print "."
    if sys.version_info < (2,7):
        print "Python version too old!"
        print "Exiting"
        sys.exit(2)
    time.sleep(1)
    print "."


    path = './probe.conf'

    print """
Successfully imported modules.
    """
    if (file_check(path)):
        print "Config file found. Skipping Configuration."
    else:
        print "No configuration file found. Creating."
        try:
            probe_conf = {}
            file_create(path)
            probe_user = "%s" % str(
                raw_input("Please provide the username the script should run under: ")).rstrip().lstrip()
            probe_conf['name'] = "%s" % str(
                raw_input("Please provide the desired name of your Mini Probe [Python MiniProbe]: ")).rstrip().lstrip()
            probe_conf['gid'] = "%s" % str(
                raw_input("Please provide the Probe GID (any unique alphanumercial string): ")).rstrip().lstrip()
            probe_conf['server'] = "%s" % str(
                raw_input("Please provide the IP/DNS name of the PRTG Core Server: ")).rstrip().lstrip()
            probe_conf['port'] = "%s" % str(raw_input(
                "Please provide the port the PRTG web server is listening to (IMPORTANT: Only SSL is supported)[443]: ")).rstrip().lstrip()
            probe_conf['baseinterval'] = "%s" % str(
                raw_input("Please provide the base interval for your sensors [60]: ")).rstrip().lstrip()
            probe_conf['key'] = "%s" % str(
                raw_input("Please provide the Probe Access Key as defined on the PRTG Core: ")).rstrip().lstrip()
            probe_path = "%s" % str(
                            raw_input("Please provide the path the probe files are located: ")).rstrip().lstrip()
            probe_cleanmem = "%s" % str(
                            raw_input("Do you want the mini probe flushing buffered and cached memory [y/N]: ")).rstrip().lstrip()
            probe_conf['announced'] = "0"
            probe_conf['protocol'] = "1"
            probe_conf['debug'] = ""
            # Handling some default values if nothing is provided
            if probe_cleanmem == "y":
                probe_conf['cleanmem'] = "True"
            else:
                probe_conf['cleanmem'] = "False"
            if not probe_conf['baseinterval']:
                probe_conf['baseinterval'] = "60"
            if not probe_conf['name']:
                probe_conf['name'] = "Python MiniProbe"
            if not probe_conf['port']:
                probe_conf['port'] = "443"
            if not probe_conf['baseinterval']:
                probe_conf['baseinterval'] = "443"
            if not (probe_conf['gid'] or probe_conf['server']):
                print "No values for GID or CORE SERVER given. Script will now exit"
                sys.exit()
            else:
                write_config(probe_conf)
                print "Config file successfully created"
                logpath = "%s/logs" % probe_path
                if not (file_check(logpath)):
                    os.makedirs(logpath)
                conf_avail = True
        except Exception, e:
            print "%s. Exiting!" % e
            conf_avail = False

    if conf_avail:
        path_rotate = "/etc/logrotate.d/MiniProbe"
        path_init = "/etc/init.d/probe.sh"
        print "Creating Logrotation Config"
        write_file(path_rotate, logrotation(probe_path))
        print "Setting up runlevel"
        write_file(path_init, init_script(probe_path, probe_user))
        print "Changing File Permissions"
        os.chmod('%s/probe.py' % probe_path, 755)
        os.chmod('/etc/init.d/probe.sh', 755)
        print subprocess.call(["update-rc.d", "probe.sh", "defaults"], shell=True)
        print "Starting Mini Probe"
        print subprocess.call("/etc/init.d/probe.sh start", shell=True)
        print "Done. You now can start/stop the Mini Probe using '/etc/init.d/probe.sh start' or  '/etc/init.d/probe.sh stop'"
    else:
        print "No Config available. Exiting!"
        sys.exit()