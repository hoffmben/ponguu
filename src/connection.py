import paho.mqtt.client as mqtt
import socket
import time
import logging
import json
import atexit
import uuid

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(log_formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


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
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()


    def recv_message(self, client, userdata, message):

        logger.info("Received message callback triggered.")
        payload = str(message.payload.decode("utf-8"))
        logger.info(f"Received message: {payload}")

        if payload:
            userdata['messages'][message.topic] = json.loads(message.payload)


    def on_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            logger.info("Connected to PongU Service")

            ip_address = get_ip_address()

            message = {'nick': self.nick, 'ip_address': ip_address, 'time': int(time.time())}
            client.publish("user_logs", json.dumps(message))
            client.subscribe([("class/recv", 1)])
        else:
            logger.error(f"Connection failed with result code {rc}")


    def publish_messages(self, message, topic="class/resp"):
        logger.info("Sending Message!")
        logger.info(f"Message:\n{message}")
        info = self.mqtt_client.publish(topic, json.dumps({'nick': self.nick, 'message': message, 'sent_time': int(time.time())}), qos=1, retain=True)
        info.wait_for_publish()


    def collect_messages(self, topic="class/recv"):
        self.mqtt_client.message_callback_add(topic, self.recv_message)
        time.sleep(3)
        return self.mqtt_client._userdata['messages']
