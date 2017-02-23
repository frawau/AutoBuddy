# AutoBuddy

AutoBuddy is a would be *Home Automation* system. Head to http://frawau.github.io/AutoBuddy/ for some description and a screenshot.

# Installation

## Appliance

By far the easiest way to install AutoBuddy is to use the appliance and run it as a virtual
machine in your network. At ths time the appliance is for KVM

The appliance can be downloaded from:
    
       https://mega.nz/#!1IUzGRyC
      
To install on a Linux host with libvirt:
    
    `virt-install --virt-type kvm --name AutoBuddy --ram 1024 \
        --disk path=<path to>/AutoBuddy.qcow2,format=qcow2 \
        --network=bridge=br0 \
        --graphics vnc,listen=<my ip> --noautoconsole \
        --os-type=linux --os-variant=ubuntutrusty --boot hd --autostart`
    
    here, <path to> is the directory where you downloaded/moved the appliance file.,
    <my ip> is your ip address

Access the console of the VM (e.g. with VNC) and answer the questions. At the end, the
VM should reboot and after a short while, you should be able to access AutoBuddy via WebBuddy,
its Web interface, at

    https://autobuddy.local:8090
    
Use "admin" with password "password" to access. It is recommended to change the password 
quickly (in the right menu)

You can also access the appliance using ssh. The username is "autobuddy", the password is what 
you set it during installation.


In WebBuddy you have two modes:
        
        Edit Mode:      Mode in whick you can create/delete zones, edit zones and
                        devices labels, move zones within zones, mode devices within 
                        zones, create/edit users
                        
                        To toggle, click on the "Edit Mode" button
                        
        User Mode:      You can send command to devices. Change your zone view.
        

### How To

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
        
### Caveat

For the VM to work, it needs to be on your network, not on some NAT'ed network. On my
Ubuntu 14.04 host machine, my /etc/network/interface file is

        auto lo
        iface lo inet loopback

        auto br0
        iface br0 inet static
                address 192.168.0.1
                network 192.168.0.0
                netmask 255.255.255.0
                broadcast 192.168.0.255
                gateway 192.168.0.254
                dns-nameservers 192.168.0.254
                dns-search doma.com domb.net
                bridge_ports eth0
                bridge_fd 9
                bridge_hello 2
                bridge_maxage 12
                bridge_stp off

If you use DHCP you could have

        auto br0
        iface br0 inet dhcp
                bridge_ports eth0
                bridge_fd 9
                bridge_hello 2
                bridge_maxage 12
                bridge_stp off
                
                
This is why you have "--network=bridge=br0" in the command to create the VM

## Manual Install

This is the begining. Installation is not for the faint of heart. I plan to soon have
an appliance image that will be easy to boot and configue using, for instance, KVM.

### What is needed

You need
 - python3
 - Postgres
 - SQLAlchemy (Python module), 
 - asyncio (Python module),
 - aiohttp (Python module),
 - ephem  (Python module)
 - dateutil (Python module),
 - lifxlan (Python module)
 
For WebBuddy you also need:
    
 - jquery.js
 - jquery-ui.min.js
 - d3.min.js  (Should be removed soon)
 - bootstrap.min.js
 - bootbox.min.js
 - Colour.js
 - bootstrap-switch.min.js
 - bootstrap-slider.min.js
 - jquery.ba-throttle-debounce.js
 - BuddyWheel.js
 
and their associated CSS files. You also need Awesome Font.

After this you need to configure all 3 components with the "-C" option
followed by the config file you want to create. For instance

    `./ControlBuddy -C /etc/autobuddy/ControlBuddy.cfg -a "autobuddy/#" \
        -b me:mypass@localhost:5672  -D postgres://me:mypass@localhost/autobuddy
        -r postgres://ro-me:passwd@localhost/autobuddy -i -z Home`

This would create a config file /etc/autotbuddy/ControlBuddy.cfg.

The address to use with AMQP would be autobuddy/# i.e. all messages for topic "autobuddy"

The AMQP broker would be on localhost at port 5672. Access with given user and password.

The Read/Write database is postgres://me:mypass@localhost/autobuddy

The read-only database access is postgres://ro-me:passwd@localhost/autobuddy. Note that these credentials
may be send to all client in case they want to access the DB directly.

The top zone nickname is "Home" and we ask the system to create it (-i)

Once this is done, you can start the ControlBuddy with

    `ControlBuddy -c /etc/autobuddy/ControlBuddy.cfg`
    
Try the "-h" option for help.

# Known Problems

At this time, only Google Chrome seems to work fully.

Firefox can not access Secure WebSocket with a self-signed certificate.

Safari and IE, status unknown, but they cannot display the colour gradient in BuddyWheel

WebSocket over IPv6 does not work. 
