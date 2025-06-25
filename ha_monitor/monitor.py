import json
import paho.mqtt.client as mqtt
import time

class ScriptMonitor:
    def __init__(self, name, broker, username, password, port=1883, base_topic="ha_monitor"):
        self.name = name
        self.broker = broker
        self.username = username
        self.password = password
        self.port = port
        self.base_topic = base_topic
        self.id = name.lower().replace(" ", "_")
        self.client = mqtt.Client(client_id=self.id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.avail_topic = f"{self.base_topic}/{self.id}/availability"
        self.state_topic = f"{self.base_topic}/{self.id}/state"
        self.attributes_topic = f"{self.base_topic}/{self.id}/attributes"
        self.disc_topic = f"homeassistant/binary_sensor/{self.id}/config"
        self.prev_iteration = 0
        
    def __enter__(self):
        self.client.username_pw_set(self.username, self.password)
        self.client.will_set(self.avail_topic, payload="offline", retain=True)
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        while not self.client.is_connected():
            time.sleep(0.1)
        self._publish_availability("online")
        self._publish_discovery()
        self._publish_state_attr("running", iteration=0, message="Started")
        return self
    
    def __exit__(self, exc_type, exc, tb):
        if exc:
            self._publish_state_attr("error", iteration=None, message="Error occurred")
            print(f"Script failed: {exc}")
        else:
            self._publish_state_attr("completed", iteration=None, message="Finished")
        
        # self._publish_availability("offline")
        
        self.client.loop_stop()
        self.client.disconnect()
        return False
    
    def _publish_discovery(self):
        payload = {
            "name": self.name,
            "unique_id": self.id,
            "state_topic": self.state_topic,
            "availability_topic": self.avail_topic,
            "json_attributes_topic": self.attributes_topic,
            "device_class": "running",  # Optional, could be "power", "connectivity", etc.
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:script-text-outline",
            "device": {
                "identifiers": ["ha_monitor"],
                "name": "HA Script Monitor",
                "model": "HA Monitor",
                "manufacturer": "AlbinEdegran",
            },
        }
        self.client.publish(self.disc_topic, json.dumps(payload), retain=True, qos=1)
    
    def _publish_availability(self, state):
        self.client.publish(self.avail_topic, state, retain=True, qos=1)
        
    def _publish_state_attr(self, status, iteration, message, qos=1):
        if iteration is None:
            iteration = self.prev_iteration
        else:
            self.prev_iteration = iteration
        payload = {
            "message": message,
            "iteration": iteration,
            "status": status,
        }
        # Publish state
        state = "ON" if status == "running" else "OFF"
        self.client.publish(self.state_topic, state, qos=qos, retain=True)
        # Publish attributes
        self.client.publish(self.attributes_topic, json.dumps(payload), qos=qos, retain=True)
        
    def update(self, *, iteration=None, status_message=None):
        self._publish_state_attr(
            status="running",
            iteration=iteration if iteration is not None else self.prev_iteration,
            message=status_message or "",
            qos=0
        )