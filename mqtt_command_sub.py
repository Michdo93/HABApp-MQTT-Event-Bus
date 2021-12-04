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
