# HABApp-MQTT-Event-Bus
A MQTT Event Bus for openHAB 2.x and 3.x using HABApp

I tested it with openHAB 3. You need at least one master and one slave. But you can also use several slaves!

## Preparation

At first you have to install [HABApp](https://habapp.readthedocs.io/en/latest/installation.html).

Then I changed the permissions with

```
sudo chown -R openhab:openhab /opt/habapp
sudo chown -R openhab:openhab /etc/openhab/habapp
```

HABApp should also work with the permissions in the installations steps. However, my problem was that the log files were not created then.

If your are using openHAB 2 instead of openHAB 3 you have to use `/etc/openhab2/habapp` instead of `/etc/openhab/habapp`.

Also you have to make sure that the systemd file looks like following:

```
[Unit]
Description=HABApp
Documentation=https://habapp.readthedocs.io
After=openhab.service

[Service]
Type=simple
User=openhab
Group=openhab
UMask=002
ExecStart=/opt/habapp/bin/habapp -c /etc/openhab/habapp

[Install]
WantedBy=multi-user.target
```

So please make sure that User and Group are openhab because it could be that there will be not logs in `/var/log/openhab2` or `/var/log/openhab`.

The next step is to install the mosquitto MQTT broker on the master with

```
sudo apt install mosquitto mosquitto-clients
```

The slaves only need `mosquitto-clients` because all slaves will later be connected to the master.

Then you have to edit the mosquitto.conf file:

```
# Place your local configuration in /etc/mosquitto/conf.d/
#
# A full description of the configuration file is at
# /usr/share/doc/mosquitto/examples/mosquitto.conf.example

listener 1883 0.0.0.0

pid_file /run/mosquitto/mosquitto.pid

persistence true
persistence_location /var/lib/mosquitto/

log_dest file /var/log/mosquitto/mosquitto.log

include_dir /etc/mosquitto/conf.d

allow_anonymous true
```

Of course you can use a password which mean you should not have to use `allow_anonymous true`. The more important thing is that you have to use `listener 1883 0.0.0.0`. This means that the mosquitto broker will be public accessible for all slaves (maybe if you want with a password).

## Configure HABapp

At first we will configure the `config.yml` for HABApp:

```
directories:
  logging: /var/log/openhab  # Folder where the logs will be written to
  rules: rules # Folder from which the rule files will be loaded
  param: params # Folder from which the parameter files will be loaded
  config: config # Folder from which configuration files (e.g. for textual thing configuration) will be loaded
  lib: lib # Folder where additional libraries can be placed
location:
  latitude: 0.0
  longitude: 0.0
  elevation: 0.0
mqtt:
  connection:
    client_id: <client_name>
    host: <public_ip_of_mosquitto_broker>
    port: 1883
    user: ''
    password: ''
    tls: false
    tls_ca_cert: ''  # Path to a CA certificate that will be treated as trusted
    tls_insecure: true
  general:
    listen_only: false  # If True HABApp will not publish any value to the broker
  publish:
    qos: 0  # Default QoS when publishing values
    retain: false # Default retain flag when publishing values
  subscribe:
    qos: 0  # Default QoS for subscribing
    topics:
    - '#'
    - 0
openhab:
  connection:
    host: <public_ip_of_openhab_instance>
    port: 8080
    user: '<openhab_user>'
    password: '<openhab_password>'
  general:
    listen_only: false  # If True HABApp will not change anything on the openHAB instance.
    wait_for_openhab: true # If True HABApp will wait for items from the openHAB instance before loading any rules on startup
  ping:
    enabled: true  # If enabled the configured item will show how long it takes to send an update from HABApp and get the updated value back from openhabin milliseconds
    item: HABApp_Ping # Name of the Numberitem
    interval: 10 # Seconds between two pings
```

The `<client_name>` can be random. On the master it could contain the word master and on the slave(s) it could be contain slave for separation. All openHAB instances should refer to the same public ip adress so `<public_ip_of_mosquitto_broker>` should be always the same. As you seen in the `mosquitto.conf` we use the public port `1883` so maybe you want to use `8883` or another port number.

If you all the anonymous access to the mosquitto broker `user` and `password` could be empty. If not fill in the username and password. I also changed `tls` to `false` and `tls_insecure` to `true`. Please check your `mosquitto.conf`! If you will use tls then you have to set `tls` to `true` and `tls_insecure` to `false`!

In the openhab section you can use `localhost` for `<public_ip_of_openhab_instance>` because it will refer to the openhab instance you are currently using. For a better separation I used the public ip address. If you are using openHAB 3 you should replace `<openhab_user>` and `<openhab_password>` with the username and password you need to access the openHAB settings panel. If you are using openHAB 2 it could be that there is no username and password needed. Please check your openHAB configuration!

In the next step we will add following to the `logging.yml` file:

```
  MQTTEventBusHandler:
    class: HABApp.core.lib.handler.MidnightRotatingFileHandler
    filename: '/var/log/openhab/EventBus.log'
    maxBytes: 1_048_576
    backupCount: 3

    formatter: Frontail_format
    level: DEBUG
```

and

```
  MQTTEventBusHandler:
    class: HABApp.core.lib.handler.MidnightRotatingFileHandler
    filename: '/var/log/openhab/EventBus.log'
    maxBytes: 1_048_576
    backupCount: 3

    formatter: Frontail_format
    level: DEBUG
```

So in my case the `config.yml` looks like this:

```
levels:
  WARNING: WARN

formatters:
  HABApp_format:
    format: '[%(asctime)s] [%(name)25s] %(levelname)8s | %(message)s'

  Frontail_format:
    format: '%(asctime)s.%(msecs)03d [%(levelname)-5s] [%(name)-36s] - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

handlers:
  # There are several Handlers available:
  #  - logging.handlers.RotatingFileHandler:
  #    Will rotate when the file reaches a certain size (see python logging documentation for args)
  #  - HABApp.core.lib.handler.MidnightRotatingFileHandler:
  #    Will wait until the file reaches a certain size and then rotate on midnight
  #  - More handlers:
  #    https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler

  HABApp_default:
    class: HABApp.core.lib.handler.MidnightRotatingFileHandler
    filename: '/var/log/openhab/HABApp.log'
    maxBytes: 1_048_576
    backupCount: 3

    formatter: Frontail_format
    level: DEBUG

  EventFile:
    class: HABApp.core.lib.handler.MidnightRotatingFileHandler
    filename: 'HABApp_events.log'
    maxBytes: 1_048_576
    backupCount: 3

    formatter: HABApp_format
    level: DEBUG

  BufferEventFile:
    class: logging.handlers.MemoryHandler
    capacity: 10
    formatter: HABApp_format
    target: EventFile
    level: DEBUG

  MQTTEventBusHandler:
    class: HABApp.core.lib.handler.MidnightRotatingFileHandler
    filename: '/var/log/openhab/EventBus.log'
    maxBytes: 1_048_576
    backupCount: 3

    formatter: Frontail_format
    level: DEBUG

loggers:
  HABApp:
    level: INFO
    handlers:
      - HABApp_default
    propagate: False

  MQTTEventBus:
    level: DEBUG
    handlers:
      - MQTTEventBusHandler
    propagate: False

  HABApp.EventBus:
    level: INFO
    handlers:
      - BufferEventFile
    propagate: False
```

This will add `EventBus.log` file to `'/var/log/openhab/`. If you are using openHAB 2 please make sure that the log file will be in `/var/log/openhab2`.

## Create the master MQTT Event Bus files

On the master you will create a `mqtt_command_sub.py` and a `mqtt_state_pub.py` file. The master will publish item states to the slave(s) and will subscribe item commands from the slave(s).

As example the `mqtt_command_sub.py` could look like this:

```
import logging
import HABApp
from HABApp.core.events import ValueUpdateEvent, ValueChangeEvent
from HABApp.openhab.items import OpenhabItem
from HABApp.mqtt.items import MqttItem

log = logging.getLogger('MQTTEventBus')


class MQTTCommandToOpenhabRule(HABApp.Rule):

    def __init__(self):
        super().__init__()

        for item in HABApp.core.Items.get_all_items():
            if not isinstance(item, OpenhabItem):
                continue
            self.listen_event('/openHAB/out/' + item.name +
                              '/command', self.on_update, ValueUpdateEvent)
            self.listen_event(
                item.name, self.item_state_change, ValueChangeEvent)

    def on_update(self, event):
        assert isinstance(event, ValueUpdateEvent)
        log.info('Subscribed MQTT topic' + event.name + ' with ' + event.value)

        itm = event.name.split("/")[3]
        cmd = event.value
        log.info(itm + ' predicted to become ' + cmd)

        self.openhab.send_command(itm, cmd)
        print(f'/openhab/{event.name} <- {event.value}')

    def item_state_change(self, event):
        assert isinstance(event, ValueChangeEvent)
        log.info(event.name + ' changed from ' +
                 event.old_value + ' to ' + event.value)


MQTTCommandToOpenhabRule()
```

As example the `mqtt_state_pub.py` could look like this:

```
import logging
import HABApp
from HABApp.openhab.events import ItemStateEvent
from HABApp.openhab.items import OpenhabItem
from HABApp.mqtt.items import MqttItem

log = logging.getLogger('MQTTEventBus')


class OpenhabStateToMQTTRule(HABApp.Rule):

    def __init__(self):
        super().__init__()

        for item in HABApp.core.Items.get_all_items():
            if not isinstance(item, OpenhabItem):
                continue
            item.listen_event(self.process_update, ItemStateEvent)

    def process_update(self, event):
        assert isinstance(event, ItemStateEvent)
        topic = '/openHAB/in/' + event.name + '/state'
        log.info('Published MQTT topic ' + topic + ' with ' + str(event.value))

        print(f'/openhab/{event.name} <- {event.value}')
        self.mqtt.publish(f'{topic}', str(event.value))


OpenhabStateToMQTTRule()
```

## Create the slave(s) MQTT Event Bus files 

On the slave(s) you will create a `mqtt_command_pub.py` and a `mqtt_state_sub.py` file. The slave(s) will subscribe item states from the master and will publish item commands to the master.

As example the `mqtt_command_pub.py` could look like this:

```
import logging
import HABApp
from HABApp.openhab.events import ItemCommandEvent
from HABApp.openhab.items import OpenhabItem
from HABApp.mqtt.items import MqttItem

log = logging.getLogger('MQTTEventBus')

class OpenhabCommandToMQTTRule(HABApp.Rule):

    def __init__(self):
        super().__init__()

        for item in HABApp.core.Items.get_all_items():
            if not isinstance(item, OpenhabItem):
                continue
            item.listen_event(self.process_update, ItemCommandEvent)

    def process_update(self, event):
        assert isinstance(event, ItemCommandEvent)
        topic = '/openHAB/out/' + event.name + '/command'
        log.info('Published MQTT topic ' + topic + ' with ' + str(event.value))

        print(f'/openhab/{event.name} <- {event.value}')
        self.mqtt.publish(f'{topic}', str(event.value))


OpenhabCommandToMQTTRule()
```

As example the `mqtt_state_sub.py` could look like this:

```
import logging
import HABApp
from HABApp.core.events import ValueUpdateEvent, ValueChangeEvent
from HABApp.openhab.items import OpenhabItem
from HABApp.mqtt.items import MqttItem

log = logging.getLogger('MQTTEventBus')


class MQTTStateToOpenhabRule(HABApp.Rule):
    """This Rule mirrors all updates from OpenHAB to MQTT"""

    def __init__(self):
        super().__init__()

        for item in HABApp.core.Items.get_all_items():
            if not isinstance(item, OpenhabItem):
                continue
            self.listen_event(
                '/openHAB/in/' + item.name + '/state', self.on_update, ValueUpdateEvent)
            self.listen_event(
                item.name, self.item_state_change, ValueChangeEvent)

    def on_update(self, event):
        assert isinstance(event, ValueUpdateEvent)
        log.info('Subscribed MQTT topic ' +
                 event.name + ' with ' + event.value)
        itm = event.name.split("/")[3]
        state = event.value

        self.openhab.post_update(itm, state)
        print(f'/openhab/{event.name} <- {event.value}')

    def item_state_change(self, event):
        assert isinstance(event, ValueChangeEvent)
        log.info(event.name + ' changed from ' +
                 event.old_value + ' to ' + event.value)


MQTTStateToOpenhabRule()
```

## Usage

You have to make sure that the item names on the master and on the slave(s) are equal. The master should contain all items from all slaves. But not all slaves should contain all items from the master. This means that the slaves can have different items with different names. Also the slaves could have only a few items from the master. This can be thought of as a restricted user who only has access to a few items. For example, that a slave is in the bathroom and the openHAB instance in the bathroom then only allows the items in the bathroom to be operated. The master/slave principle can only subscribe where the corresponding item is present. Otherwise it will be published, but a slave or even none of the slaves will access this topic. Conversely, the master should be able to subscribe to everything that the slaves publish.

## Check the master logging

The `EventBus.log` on the master could look like this:

```
2021-12-04 00:35:02.326 [INFO ] [MQTTEventBus                        ] - Published MQTT topic /openHAB/in/testSwitch/state with ON
2021-12-04 00:35:02.332 [INFO ] [MQTTEventBus                        ] - testSwitch changed from OFF to ON
2021-12-04 00:35:09.845 [INFO ] [MQTTEventBus                        ] - Subscribed MQTT topic/openHAB/out/testSwitch/command with OFF
2021-12-04 00:35:09.846 [INFO ] [MQTTEventBus                        ] - testSwitch predicted to become OFF
2021-12-04 00:35:09.889 [INFO ] [MQTTEventBus                        ] - Published MQTT topic /openHAB/in/testSwitch/state with OFF
2021-12-04 00:35:09.894 [INFO ] [MQTTEventBus                        ] - testSwitch changed from ON to OFF
2021-12-04 00:35:16.777 [INFO ] [MQTTEventBus                        ] - Subscribed MQTT topic/openHAB/out/testSwitch/command with ON
2021-12-04 00:35:16.779 [INFO ] [MQTTEventBus                        ] - testSwitch predicted to become ON
2021-12-04 00:35:16.817 [INFO ] [MQTTEventBus                        ] - Published MQTT topic /openHAB/in/testSwitch/state with ON
2021-12-04 00:35:16.823 [INFO ] [MQTTEventBus                        ] - testSwitch changed from OFF to ON
2021-12-04 00:35:20.787 [INFO ] [MQTTEventBus                        ] - Published MQTT topic /openHAB/in/testSwitch/state with OFF
2021-12-04 00:35:20.792 [INFO ] [MQTTEventBus                        ] - testSwitch changed from ON to OFF
```

## Check the slave logging

The `EventBus.log` on the slave(s) could look like this:

```
2021-12-04 00:35:02.337 [INFO ] [MQTTEventBus                        ] - Subscribed MQTT topic /openHAB/in/testSwitch/state with ON
2021-12-04 00:35:02.396 [INFO ] [MQTTEventBus                        ] - testSwitch changed from OFF to ON
2021-12-04 00:35:09.837 [INFO ] [MQTTEventBus                        ] - Published MQTT topic /openHAB/out/testSwitch/command with OFF
2021-12-04 00:35:09.847 [INFO ] [MQTTEventBus                        ] - testSwitch changed from ON to OFF
2021-12-04 00:35:09.893 [INFO ] [MQTTEventBus                        ] - Subscribed MQTT topic /openHAB/in/testSwitch/state with OFF
2021-12-04 00:35:16.767 [INFO ] [MQTTEventBus                        ] - Published MQTT topic /openHAB/out/testSwitch/command with ON
2021-12-04 00:35:16.781 [INFO ] [MQTTEventBus                        ] - testSwitch changed from OFF to ON
2021-12-04 00:35:16.821 [INFO ] [MQTTEventBus                        ] - Subscribed MQTT topic /openHAB/in/testSwitch/state with ON
2021-12-04 00:35:20.792 [INFO ] [MQTTEventBus                        ] - Subscribed MQTT topic /openHAB/in/testSwitch/state with OFF
2021-12-04 00:35:20.831 [INFO ] [MQTTEventBus                        ] - testSwitch changed from ON to OFF
```

## Configure the Event Bus topics

As example you have:

```
# mqtt_command_pub
'/openHAB/out/' + event.name + '/command'

# mqtt_command_sub
'/openHAB/out/' + item.name + '/command'

# mqtt_state_pub
'/openHAB/in/' + event.name + '/state'

# mqtt_state_sub
'/openHAB/in/' + item.name + '/state'
```

So I used a leading `/`. If you don't want to use a leading `/` so that you use as example `'openHAB/in/' + event.name + 'state'` instead of `'/openHAB/in' + event.name + 'state'` you have to change

```
event.name.split("/")[3]
```

to

```
event.name.split("/")[2]
```

on the `mqtt_state_sub.py` file. This is equivalent to the `mqtt_command_sub.py` file.

Also you have to change the publisher in the `mqtt_state_pub.py` and the `mqtt_command_pub.py` files. There you have to remove the leading `/` inside the string argument of the `self.listen_event` function.

So if you also want to remove `out/` and `in/` it will be changed to `event.name.split("/")[1]`.

You can also create and use completely different topic names. You just have to make sure that the changes are adjusted accordingly in all files. The item name is best separated by a / when subscribing. Count the number of slashes and enter this for the split command accordingly!

I hope this example was self-explanatory.

I hope you like this!
