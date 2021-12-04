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
