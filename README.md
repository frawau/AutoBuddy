# AutoBuddy

AutoBuddy is a would be *Home Automation* system. Head to http://frawau.github.io/AutoBuddy/ for some description and some screenshots.

# Raspberry Pi Installation

RPi3 and RPi2 are supported.

It is not recommended to use Wifi with RPi3. In any case, you'll need a wired network connection for this installation.

Download the image from [this link at Google Drive](https://drive.google.com/file/d/0B-JicGkaZAeXSElCby1LdDgzVGM/view?usp=sharing)

Write the image to an SD card the usual way

    xzcat rpi3-autobuddy.img.xz | dd of=/dev/sdX

with X the actual device e.g. sdb, sdc, ...

Boot the RPi and connect to it using ssh;

    ssh autobuddy@autobuddy.local

The password is "autobuddy" (without the quotes)


Update AutoBuddy

    cd Autobuddy
    git pull
    cd ..


Configure

    sudo AutoBuddy/ConfigBuddy/ConfigBuddy

answer the questions and reboot.

Access WebBuddy at

    https://autobuddy.local:8090

If it complains about an unsafe connection, ignore and trust the self-signed certificates
then login as user "admin" with password "password"

Have fun and let us know what you like or don't like..

# Installation

## Requirements

AutoBuddy depends on a quite a few softwares. To start, you must have Python 3.5 or newer, so you need a fairly
recent distribution. On Raspberry Pi, you can use Jessie and use Stretch to update the Python sub-system.

To install all the needed packages, on a recent Ubuntu/Debian distro, you could run

    sudo apt -y install postgresql tmux python3-sqlalchemy python3-crypto python3-psycopg2 python3-zeronconf \
                        python3-ephem python3-dateutil python3-crontab python3-bitstring python3-pip git
    sudo pip3 install aiolifx aioarping aiobtname aioblescan pyalsaaudio aiohttp aiocoap zeroconf aiodns

You must make sure that Postgres is running! Currently (03/17), the configuration tool will blissfully
ignore any error when trying to set up the datanase (If asked to that is).

If you plan on using KodiBuddy the python3-aiohttp package won't work, you need aiohttp from PyPi.

On a Ubuntu/Debian distro, you can test that Postgres is running OK by doing, in a terminal:

    sudo bash
          Type your passwordif asked to
    su postgres
    psql

If you get something like

    psql (9.6.2)
    Type "help" for help.

    postgres=#

You are all set. This also means you can use "sudo" to run the configuration script, which will make your life
a lot easier.

To get out of there use:

    \q
    ctrl-d
    ctrl-d



## Installing AutoBuddy

Just clone from github:

    git clone https://github.com/frawau/AutoBuddy

Once the repository has been cloned, you can run the installation script. If you could access Postgres using the method
described above AND if you trust the script, you can do

    sudo AutoBuddy/ConfigBuddy/ConfigBuddy

If not, either you can provide a postgres "superuser" name and password, or the configuration script
will do what it can and tell you, at the end, what you still need to do (SQL command, python script...).
Simply run the script as:

    AutoBuddy/ConfigBuddy/ConfigBuddy

WARNING: Running the configuration script with sudo will automatically grant "raw socket" privileges to
the python interpreter. Some people may object to this.


ConfigBuddy will ask you a few question and proceed to create a number of files/directories.

    AutoBuddy/.tls/              for certificates
    AutoBuddy/.buddyconfig/      for the json configuration files
    AutoBuddy/.run/              for the various starting files
    AutoBuddy/.start-autobuddy   the file starting the applications in tmux sessions.
    AutoBuddy/.stop-autobuddy    the file stopping the applications.

At the end it will also schedule AutoBuddy/.start-autobuddy to start on boot by adding an "autobuddy" service
to systemd. If you want to run AutoBuddy as an unprivildged user, you could schedule it to run at boot time
with crontab "@boot"

If you did not run under sudo, or did not provide username and password for Postgres, ConfigBuddy
will list all the actions that need to be done:

    - Database creation. SQL commands
    - Database user, password and privileges. SQL commands
    - Bootstrap the AutoBuddy database. Python script
    - Needed 'setcap'. Shell commands

If you provided the wrong username/password for Postgres, you'll have to run ConfigBuddy again.


If everything went OK, you can run AutoBuddy by either:

    1- rebooting
    2- run AutoBuddy/.start-autobuddy

After 30/45 seconds, you can access WebBuddy at:

    https://localhost:8090

Use "admin" with password "password" to access. It is recommended to change the password
quickly (in the right menu)


### How To

In WebBuddy you have two modes:

        Edit Mode:      Mode in whick you can create/delete zones, edit zones and
                        devices labels, move zones within zones, mode devices within
                        zones, create/edit users

                        To toggle, click on the "Edit Mode" button

        User Mode:      You can send command to devices (click on device).
                        Get device info if any (Ctrl-Click on device)
                        Change your zone view. (Double-Click zone)


Here is how you do a few things:
    In User Mode
        To send a command to a device, click on the device.
        To send a command to a zone, click on the zone label
        To change zone view, double click on the zone

    In Edit Mode:
        Create a new zone: drag-and-drop the "New Zone" label into a zone
        Delete a zone: drag-and-drop the zone to the "Delete" label
        Move a zone: drag-and-drop the zone into a zone
        Move a device: drag-and-drop the device into a zone
        Label a device: double-click the device
        Label a zone: double-click the zone

    In Rules trigger, condition and action as well as logger, when you need to
    specify the part of the value you are interrested in, specify with "::", e.g.
            value::accelerometer::vector
            value::power
    Most of the time you'll start with "value"

The Menu also contains quite a few things.

    Commands (for instance to associate a flic button with FlicBuddy)
    Configurations (Who's presence to look for, what rules for automation,...)
    Graphs (To graph logged data)


# Known Problems


Actually more like missing features....

Play music by artist

Parametrize Voice uterances
