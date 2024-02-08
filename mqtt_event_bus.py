import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import string
import random
import logging
import concurrent.futures
from typing import List
import HABApp
from HABApp import Parameter
from HABApp.core.events import ValueChangeEvent, ValueUpdateEvent
from HABApp.openhab.events import ItemCommandEvent, ItemStateEvent
from HABApp.core.events import ValueChangeEventFilter, ValueUpdateEventFilter
from HABApp.openhab.events import ItemCommandEventFilter, ItemStateEventFilter
from HABApp.core.events import EventFilter
from HABApp.openhab.items import OpenhabItem

log = logging.getLogger('MQTTEventBus')

log_state = Parameter('mqtt_event_bus', 'log_state', default_value=True).value


class MqttEventBus(HABApp.Rule):
    def __init__(self):
        super().__init__()

        self.onInit = Parameter(
            'mqtt_event_bus', 'onInit', default_value=True).value
        self.brokerTransport = Parameter(
            'mqtt_event_bus', 'brokerTransport', default_value="tcp").value
        self.brokerIP = Parameter(
            'mqtt_event_bus', 'brokerIP', default_value="192.168.0.5").value
        self.brokerPort = Parameter(
            'mqtt_event_bus', 'brokerPort', default_value=1883).value
        self.clientId = Parameter(
            'mqtt_event_bus', 'clientId', default_value="OpenHABVM").value
        self.tlsPath = Parameter(
            'mqtt_event_bus', 'tlsPath', default_value="").value
        self.tlsVersion = Parameter(
            'mqtt_event_bus', 'tlsVersion', default_value="").value
        self.brokerUser = Parameter(
            'mqtt_event_bus', 'brokerUser', default_value="").value
        self.brokerPWD = Parameter(
            'mqtt_event_bus', 'brokerPWD', default_value="").value
        self.brokerQOS = Parameter(
            'mqtt_event_bus', 'brokerQOS', default_value=1).value
        self.retain = Parameter(
            'mqtt_event_bus', 'retain', default_value="").value
        self.brokerAsync = Parameter(
            'mqtt_event_bus', 'brokerAsync', default_value="").value
        self.statePublishTopic = Parameter(
            'mqtt_event_bus', 'statePublishTopic', default_value="/messages/states/${item}").value
        self.commandPublishTopic = Parameter(
            'mqtt_event_bus', 'commandPublishTopic', default_value="").value
        self.stateSubscribeTopic = Parameter(
            'mqtt_event_bus', 'stateSubscribeTopic', default_value="").value
        self.commandSubscribeTopic = Parameter(
            'mqtt_event_bus', 'commandSubscribeTopic', default_value="/messages/commands/${item}").value

        rand = "".join(random.choice(string.ascii_uppercase + string.digits)
                       for _ in range(3))

        if self.brokerQOS not in range(0, 3):
            self.brokerQOS = 0

        self.auth = None
        if self.brokerUser is not None:
            if self.brokerPWD is not None:
                self.auth = {'username': self.brokerUser,
                             'password': self.brokerPWD}
            else:
                self.auth = {'username': self.brokerUser,
                             'password': ""}
        else:
            self.auth = None

        if self.brokerUser == "" or self.brokerUser == None:
            self.auth = None

        self.broker_tls = None
        if self.brokerPort != 1883:
            if self.tlsPath is not None or self.tlsPath != "":
                if self.tlsVersion is not None or self.tlsVersion != "":
                    self.broker_tls = (self.tlsPath, self.tlsVersion)
                else:
                    self.broker_tls = self.tlsPath
            else:
                self.broker_tls = None

        self.client = mqtt.Client(client_id=self.clientId[:20]+rand, clean_session=True,
                                  userdata=None, protocol=mqtt.MQTTv311, transport=self.brokerTransport)

        if self.broker_tls is not None:
            self.client.tls_set(self.broker_tls)

        if self.retain == True:
            self.retain = True
        else:
            self.retain = False

        if self.brokerAsync == True:
            self.brokerAsync = True
        else:
            self.brokerAsync = False

        self.topics = []

        with concurrent.futures.ProcessPoolExecutor() as executor:
            for item in self.get_items(type=OpenhabItem):
                if self.statePublishTopic:
                    if self.onInit:
                        executor.submit(self.on_init_item(
                            item.name, item.get_value(), self.statePublishTopic), item.name)
                    executor.submit(item.listen_event(
                        self.on_item_state, event_filter=ItemStateEventFilter()), item.name)

                if self.commandPublishTopic:
                    executor.submit(item.listen_event(
                        self.on_item_command, event_filter=ItemCommandEventFilter()), item.name)

                if self.commandSubscribeTopic:
                    tpc = self.commandSubscribeTopic.replace(
                        "${item}", str(item.name))
                    executor.submit(self.topics.append(
                        (tpc, self.brokerQOS)), item.name)

                if self.stateSubscribeTopic:
                    tpc = self.stateSubscribeTopic.replace(
                        "${item}", str(item.name))
                    executor.submit(self.topics.append(
                        (tpc, self.brokerQOS)), item.name)

            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.username_pw_set(self.auth)

            if self.brokerAsync:
                self.client.connect_async(self.brokerIP, self.brokerPort)
            else:
                self.client.connect(self.brokerIP, self.brokerPort)

            #self.client.loop_forever()
            self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe(self.topics)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        stateOrCommand = str(msg.payload.decode("utf-8"))

        log.info(
            f'Subscribed MQTT topic {topic} with {stateOrCommand}')

        if self.stateSubscribeTopic:
            event_type = 'state'
            itemPosition = self.stateSubscribeTopic.split("${item}")[
                0].count("/")

        if self.commandSubscribeTopic:
            event_type = 'command'
            itemPosition = self.commandSubscribeTopic.split("${item}")[
                0].count("/")

        item_name = topic.split("/")[itemPosition]

        if self.openhab.item_exists(item_name) == True:
            if event_type == "command":
                self.openhab.send_command(
                    item_name, stateOrCommand)

                log.info(
                    f'Item {item_name} received command {stateOrCommand}')
            elif event_type == "state":
                self.openhab.post_update(item_name, stateOrCommand)
                log.info(
                    f'Item {item_name} received update {stateOrCommand}')

    def on_init_item(self, item, value, topicString):
        topicString = topicString.replace("${item}", item)
        topic = f'{topicString}'

        log.info(f'Published MQTT topic {topic} with {value}')

        rand = "".join(random.choice(string.ascii_uppercase + string.digits)
                       for _ in range(3))

        publish.single(topic=topic, payload=str(value), qos=self.brokerQOS, retain=self.retain, hostname=self.brokerIP,
                       port=self.brokerPort, client_id=self.clientId[:20]+rand, keepalive=60, will=None,
                       auth=self.auth, tls=self.broker_tls,
                       protocol=mqtt.MQTTv311, transport=self.brokerTransport)

    def on_item_state(self, event: ItemStateEvent):
        topicString = self.statePublishTopic.replace(
            "${item}", event.name)
        topic = f'{topicString}'
        value = event.value

        log.info(f'Published  MQTT topic {topic} with {value}')

        rand = "".join(random.choice(string.ascii_uppercase + string.digits)
                       for _ in range(3))

        publish.single(topic=topic, payload=str(value), qos=self.brokerQOS, retain=self.retain, hostname=self.brokerIP,
                       port=self.brokerPort, client_id=self.clientId[:20]+rand, keepalive=60, will=None,
                       auth=self.auth, tls=self.broker_tls,
                       protocol=mqtt.MQTTv311, transport=self.brokerTransport)

    def on_item_command(self, event: ItemCommandEvent):
        topicString = self.commandPublishTopic.replace(
            "${item}", event.name)
        topic = f'{topicString}'
        value = event.value

        log.info(f'Published  MQTT topic {topic} with {value}')

        rand = "".join(random.choice(string.ascii_uppercase + string.digits)
                       for _ in range(3))

        publish.single(topic=topic, payload=str(value), qos=self.brokerQOS, retain=self.retain, hostname=self.brokerIP,
                       port=self.brokerPort, client_id=self.clientId[:20]+rand, keepalive=60, will=None,
                       auth=self.auth, tls=self.broker_tls,
                       protocol=mqtt.MQTTv311, transport=self.brokerTransport)


class LogItemStateRule(HABApp.Rule):
    """This rule logs the item state in the mqtt event bus log file"""

    def __init__(self):
        super().__init__()

        with concurrent.futures.ProcessPoolExecutor() as executor:
            for item in self.get_items(type=OpenhabItem):
                executor.submit(item.listen_event(
                    self.on_item_change, ValueChangeEventFilter()), item.name)

    def on_item_change(self, event:ValueChangeEvent):
        assert isinstance(event, ValueChangeEvent), type(event)
        log.info(f'{event.name} changed from {event.old_value} to {event.value}')


MqttEventBus()

# Create logger rule only if configured
if log_state:
    LogItemStateRule()
