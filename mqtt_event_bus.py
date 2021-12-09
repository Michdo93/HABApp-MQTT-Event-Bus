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
            self.openhab.post_update(item.name, item.get_value())
            self.openhab.send_command(item.name, item.get_value())
            if statePublishTopic != '':
                item.listen_event(self.on_item_state, ItemStateEvent)

            if commandPublishTopic != '':
                item.listen_event(self.on_item_command, ItemCommandEvent)

            if commandSubscribeTopic != '':
                topic_command = commandSubscribeTopic.replace(
                    "${item}", str(item.name))

                mqtt_item_command = MqttItem.get_create_item(
                    f'{topic_command}')
                mqtt_item_command.listen_event(
                    self.on_mqtt_command, ValueUpdateEvent)

            if stateSubscribeTopic != '':
                topic_state = stateSubscribeTopic.replace(
                    "${item}", str(item.name))

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

        self.mqtt.publish(topic, str(value), true)

    def on_item_command(self, event: ItemCommandEvent):
        topicString = commandPublishTopic.replace(
            "${item}", event.name)
        topic = f'{topicString}'
        value = event.value

        log.info(f'Published  MQTT topic {topic} with {value}')

        self.mqtt.publish(topic, str(value))

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
