import paho.mqtt.client as mqtt
import socket
import time
import logging
import json
import atexit
import uuid
import base64

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(log_formatter)
logger.addHandler(handler)


def get_ip_address():
    # Create a socket to get the local IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip_address = s.getsockname()[0]
    finally:
        s.close()
    return ip_address


class PongU:

    def __init__(self, nick: str, 
                 srvr_username: str, srvr_password: str, srvr_location: str, srvr_port: int=1883,
                 verbose=False, **kwargs):
        """Sends and receives messages to/from the PongU MQTT broker.

        Args:
            nick (str): username
            srvr_username (str): broker username
            srvr_password (str): broker password
            srvr_location (str): broker host location
            srvr_port (int, optional): broker port number. Defaults to 1883.
        """

        self.nick = nick
        unique_id = str(uuid.uuid4())
        client_id = f"{self.nick}_{unique_id}"

        self.null_userdata = kwargs.get('userdata', {'messages': {}})
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                       client_id=client_id,
                                       clean_session=True,
                                       userdata=self.null_userdata)
        self.srvr_location = srvr_location
        self.srvr_port = srvr_port

        if verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        atexit.register(self.__close_connection)

        # Set the username and password for authentication
        self.mqtt_client.username_pw_set(srvr_username, srvr_password)

        # Set the connection callback function
        self.mqtt_client.on_connect = self.on_connect

        logger.info("Opening connection")
        self.mqtt_client.connect(self.srvr_location, self.srvr_port)
        self.mqtt_client.loop_start()


    def client_connect(self):
        logger.info("Opening connection")
        self.mqtt_client.connect(self.srvr_location, self.srvr_port)


    def __close_connection(self):
        logger.info("Closing connection")
        self.mqtt_client.disconnect()


    def recv_message(self, client, userdata, message):

        logger.info("Received message callback triggered.")

        try:
            payload = base64.b64decode(message.payload)
            payload = json.loads(payload.decode('utf-8'))
        except Exception as e:
            logger.error("Failed to parse Message: %s", e)
        logger.info(f"Received message: {payload}")

        if payload:
            userdata['messages'][message.topic] = payload


    def on_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            logger.info("Connected to PongU Service")

            ip_address = get_ip_address()

            json_bytes = json.dumps({'nick': self.nick, 'ip_address': ip_address, 'time': int(time.time())}).encode('utf-8')
            base64_encoded_data = base64.b64encode(json_bytes)
            client.publish("user_logs", base64_encoded_data)
            client.subscribe([("class/recv", 1)])
        else:
            logger.error(f"Connection failed with result code {rc}")


    def publish_messages(self, message, topic="class/resp"):
        logger.info("Sending Message!")
        logger.info(f"Message:\n{message}")

        json_bytes = json.dumps({'nick': self.nick, 'message': message, 'sent_time': int(time.time())}).encode('utf-8')
        base64_encoded_data = base64.b64encode(json_bytes)

        info = self.mqtt_client.publish(topic, base64_encoded_data, qos=1, retain=True)
        info.wait_for_publish()


    def collect_messages(self, topic="class/recv"):
        self.mqtt_client.subscribe([(topic, 1)])
        self.mqtt_client.message_callback_add(topic, self.recv_message)
        time.sleep(3)
        return self.mqtt_client._userdata['messages']
