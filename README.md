# AutoBuddy

AutoBuddy is a would be *Home Automation* system. Head to http://frawau.github.io/AutoBuddy/ for some description and a screenshot.

# Instalation

This is the begining. Installation is not for the faint of heart. I plan to soon have
an appliance image that will be easy to boot and configue using, for instance, KVM.

##What is needed

You need
 - Apache Qpid configured with SSL
 - Install SQLAlchemy, 
 - qpid python library, 
 - Twisted, 
 - Autobahn WS python library
 - lifxlan python library
 
For WebBuddy you also need:
    
 - jquery.js
 - jquery-ui.min.js
 - d3.min.js  (Should be remove soon)
 - bootstrap.min.js"
 - bootbox.min.js
 - Colour.js
 - bootstrap-switch.min.js
 - bootstrap-slider.min.js
 - BuddyWheel.js
 
and their associated CSS files. You also need Awesome Font.

After this you need to configure all 5 components with the "-C" option
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

The top zone nickname is "Home" and we ask the system to create if (-i)

Once this is done, you can start the ControlBuddy with

    `ControlBuddy -c /etc/autobuddy/ControlBuddy.cfg`
    
Try the "-h" option for help.

#Known Problems

At this time, only Google Chrome seems to work fully.

Firefox can not access Secure WebSocket with a signed certificate.

Safari and IE, status unknown, but they cannot display the colour gradient in BuddyWheel

WebSocket over IPv6 does not work. 
