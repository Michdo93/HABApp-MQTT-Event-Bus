# HABApp-MQTT-Event-Bus
A MQTT Event Bus for openHAB 2.x and 3.x using HABApp. Tested with openHAB 3. This should work equivalent like the [Event bus binding](https://v2.openhab.org/addons/bindings/mqtt1/#event-bus-binding-configuration) from the old [MQTT 1.x binding](https://v2.openhab.org/addons/bindings/mqtt1/).

Description:
Publish/receive all states/commmands directly on the openHAB eventbus.

Usage:
Perfect for integrating multiple openHAB instances or broadcasting all events.

## Preparation

### Install HABApp

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

### Install the mosquitto MQTT broker

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

### Configure HABapp

#### Configure the MQTT and openHAB connection

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

#### Configure the logging handler

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

## Installation

You can install it for openHAB 3 with:

```
wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/mqtt_event_bus.py -P /etc/openhab/habapp/rules
sudo chmod +x /etc/openhab/habapp/rules/mqtt_event_bus.py
sudo chown -R openhab:openhab /etc/openhab/habapp/rules/mqtt_event_bus.py
```

And for openHAB 2 with:

```
wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/mqtt_event_bus.py -P /etc/openhab2/habapp/rules
sudo chmod +x /etc/openhab2/habapp/rules/mqtt_event_bus.py
sudo chown -R openhab:openhab /etc/openhab2/habapp/rules/mqtt_event_bus.py
```

or copy this code and create a file with `sudo nano /etc/openhab/habapp/rules/mqtt_event_bus.py` or `sudo nano /etc/openhab2/habapp/rules/mqtt_event_bus.py`

```
import logging

import HABApp
from HABApp import Parameter
from HABApp.core.events import ValueChangeEvent, ValueUpdateEvent
from HABApp.mqtt.items import MqttItem
from HABApp.openhab.events import ItemCommandEvent, ItemStateEvent
from HABApp.openhab.items import OpenhabItem

log = logging.getLogger('MQTTEventBus')

# These are the configuration values that will be used to setup the MqttEventBus
log_state = Parameter('mqtt_event_bus', 'log_state', default_value=True).value
statePublishTopic = Parameter(
    'mqtt_event_bus', 'statePublishTopic', default_value='').value
commandPublishTopic = Parameter(
    'mqtt_event_bus', 'commandPublishTopic', default_value='').value
stateSubscribeTopic = Parameter(
    'mqtt_event_bus', 'stateSubscribeTopic', default_value='').value
commandSubscribeTopic = Parameter(
    'mqtt_event_bus', 'commandSubscribeTopic', default_value='').value


class MqttEventBus(HABApp.Rule):
    def __init__(self):
        super().__init__()

        for item in self.get_items(type=OpenhabItem):
            if statePublishTopic != '':
                item.listen_event(self.on_item_state, ItemStateEvent)

            if commandPublishTopic != '':
                item.listen_event(self.on_item_command, ItemCommandEvent)

            if commandSubscribeTopic != '':
                topic_command = commandSubscribeTopic.replace(
                    "${item}", item.name)

                mqtt_item_command = MqttItem.get_create_item(f'{topic_command}')
                mqtt_item_command.listen_event(
                    self.on_mqtt_command, ValueUpdateEvent)

            if stateSubscribeTopic != '':
                topic_state = stateSubscribeTopic.replace(
                    "${item}", item.name)

                mqtt_item_state = MqttItem.get_create_item(f'{topic_state}')
                mqtt_item_state.listen_event(
                    self.on_mqtt_state, ValueUpdateEvent)

    def on_mqtt_command(self, event):
        assert isinstance(event, ValueUpdateEvent)

        name = event.name
        itemPosition = commandSubscribeTopic.split("${item}")[0].count("/")

        item = name.split("/")[itemPosition]
        cmd = event.value

        log.info(f'Subscribed MQTT topic {event.name} with {cmd}')
        log.info(f'{item} predicted to become {cmd}')

        self.openhab.send_command(item, cmd)

    def on_item_state(self, event: ItemStateEvent):
        topicString = statePublishTopic.replace(
            "${item}", event.name)
        topic = f'{topicString}'
        value = event.value

        log.info(f'Published  MQTT topic {topic} with {value}')

        self.mqtt.publish(topic, value)

    def on_item_command(self, event: ItemCommandEvent):
        topicString = commandPublishTopic.replace(
            "${item}", event.name)
        topic = f'{topicString}'
        value = event.value

        log.info(f'Published  MQTT topic {topic} with {value}')

        self.mqtt.publish(topic, value)

    def on_mqtt_state(self, event):
        assert isinstance(event, ValueUpdateEvent)

        name = event.name
        itemPosition = stateSubscribeTopic.split("${item}")[0].count("/")

        item = name.split("/")[itemPosition]
        state = event.value

        log.info(f'Subscribed MQTT topic {name} with {state}')
        self.openhab.post_update(item, state)


class LogItemStateRule(HABApp.Rule):
    """This rule logs the item state in the mqtt event bus log file"""

    def __init__(self):
        super().__init__()

        for item in self.get_items(type=OpenhabItem):
            item.listen_event(self.on_item_change, ValueChangeEvent)

    def on_item_change(self, event):
        assert isinstance(event, ValueChangeEvent)
        log.info(f'{event.name} changed from {event.old_value} to {event.value}')


MqttEventBus()

# Create logger rule only if configured
if log_state:
    LogItemStateRule()
```

After that you have to restart habapp with:

```
sudo systemctl restart habapp.service
```

This should create a file like this in `/etc/openhab/habapp/params/mqtt_event_bus.yml` or `/etc/openhab2/habapp/params/mqtt_event_bus.yml`:

```
log_state: true
statePublishTopic: ''
commandPublishTopic: ''
stateSubscribeTopic: ''
commandSubscribeTopic: ''
```

If not you can create it with `sudo nano /etc/openhab/habapp/params/mqtt_event_bus.yml` or `sudo nano /etc/openhab2/habapp/params/mqtt_event_bus.yml`. Alternatively you can download it with `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/mqtt_event_bus.yml -O /etc/openhab/habapp/params/mqtt_event_bus.yml` or `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/mqtt_event_bus.yml -O /etc/openhab2/habapp/params/mqtt_event_bus.yml`.

## Master / Slave example

Please make sure that the slave(s) will be connected to the master's mosquitto broker!

### Usage

You have to make sure that the item names on the master and on the slave(s) are equal. The master should contain all items from all slaves. But not all slaves should contain all items from the master. This means that the slaves can have different items with different names. Also the slaves could have only a few items from the master. This can be thought of as a restricted user who only has access to a few items. For example, that a slave is in the bathroom and the openHAB instance in the bathroom then only allows the items in the bathroom to be operated. The master/slave principle can only subscribe where the corresponding item is present. Otherwise it will be published, but a slave or even none of the slaves will access this topic. Conversely, the master should be able to subscribe to everything that the slaves publish.

### Configuration example 1

On the master you can create a configuration like this:

```
log_state: true
statePublishTopic: openHAB/in/${item}/state
commandPublishTopic: ''
stateSubscribeTopic: ''
commandSubscribeTopic: openHAB/out/${item}/command
```

and on the slave like this:

```
log_state: true
statePublishTopic: ''
commandPublishTopic: openHAB/out/${item}/command
stateSubscribeTopic: openHAB/in/${item}/state
commandSubscribeTopic: ''
```

Or on the master you can download it with `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.master1 -O /etc/openhab/habapp/params/mqtt_event_bus.yml` or `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.master1 -O /etc/openhab2/habapp/params/mqtt_event_bus.yml`. On the slave you can download it with `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.slave1 -O /etc/openhab/habapp/params/mqtt_event_bus.yml` or `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.slave1 -O /etc/openhab2/habapp/params/mqtt_event_bus.yml`.

### Configuration example 2

On the master you can create a configuration like this:

```
log_state: true
statePublishTopic: /messages/states/${item}
commandPublishTopic: ''
stateSubscribeTopic: ''
commandSubscribeTopic: /messages/commands/${item}
```

and on the slave like this:

```
log_state: true
statePublishTopic: ''
commandPublishTopic: /messages/commands/${item}
stateSubscribeTopic: /messages/states/${item}
commandSubscribeTopic: ''
```

Or on the master you can download it with `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.master2 -O /etc/openhab/habapp/params/mqtt_event_bus.yml` or `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.master2 -O /etc/openhab2/habapp/params/mqtt_event_bus.yml`. On the slave you can download it with `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.slave2 -O /etc/openhab/habapp/params/mqtt_event_bus.yml` or `wget https://raw.githubusercontent.com/Michdo93/HABApp-MQTT-Event-Bus/main/example/mqtt_event_bus.yml.slave2 -O /etc/openhab2/habapp/params/mqtt_event_bus.yml`.

### Proof of concept

#### Check the master logging

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

#### Check the slave logging

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
