import enum
import ipaddress
import random
import string
import subprocess
import asyncio
import time

from ipaddress import IPv6Address
from dataclasses import dataclass, field
import logging
import aiocoap
from aiocoap import *
from aiocoap.protocol import Request

# For Network
import socket
from zeroconf import ServiceInfo
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

# Declare Variable
ADVERT_TIMING_INTERVAL_S = 30
COAP_UDP_DEFAULT_PORT = 5683


class OtDeviceType(enum.IntEnum):
    GasSent = 0
    UNKNOWN = -255


@dataclass
class OtDevice:
    """ Generic class for an OpenThread device. """
    device_type: OtDeviceType = field(default=OtDeviceType.UNKNOWN)
    eui64: int = field(default=0)
    uri: str = field(default="")
    last_seen: float = field(default=0)


@dataclass
class OtGS(OtDevice):
    """ Class to store information about GasSentinel """
    temperature: int = field(default=0)
    humidity: int = field(default=0)
    pressure: int = field(default=0)
    cl1: int = field(default=0)
    cl2: int = field(default=0)
    rssi: int = field(default=0)
    vdd: int = field(default=0)


class ServerManager:
    """ This class manages the ot clients and associated information.New children are
    found when the client sends a message to a known resource on the server"""

    client_ip6 = dict[IPv6Address, OtDevice]()  # create dictionary of clients accepting service - sensitivity list
    self_ip6 = ipaddress.IPv6Address  # CoAP server IPv6

    # Queue for new children to be allocated a resource
    incoming_queue_child_ips = set[IPv6Address]()
    pend_queue_child_ips = set[IPv6Address]()

    def __init__(self, self_ip: IPv6Address):
        self.self_ip6 = self_ip
        self.zeroconf = Zeroconf()  # Create Zeroconf instance

    async def advertise_server(self):
        """Advertise server's service periodically"""

        # Define the service information
        service_name = "My CoAP Server"
        service_type = "_coap._udp.local."  # CoAP service type
        device_port = COAP_UDP_DEFAULT_PORT

        # Create the service info object
        service_info = ServiceInfo(
            service_type,
            f"{service_name}.{service_type}",
            addresses=[socket.inet_pton(socket.AF_INET6, str(self.self_ip6))],
            port=device_port,
            properties={},
        )
        try:
            self.zeroconf.register_service(service_info)  # Register the service
            logging.info("Successful: Server Advertised")

        except KeyError:
            logging.warning("unsuccessful: Server Not Advertised")
            raise KeyError

        await asyncio.sleep(ADVERT_TIMING_INTERVAL_S)

    def get_all_child_ips(self):
        """ Returns a dict of all children in the sensitivity list. """
        return self.client_ip6

    def allocate_resource(self, ip: IPv6Address):
        """Allocate a resource to the client based on its EUI64."""
        # Generate a unique URI for the client based on a slice of its EUI64
        eui64 = self.client_ip6[ip].eui64
        resource = str(eui64)[:8]  # Take a slice of the EUI64 to use as the resource
        self.client_ip6[ip].uri = resource
        logging.info(f"Allocated resource {resource} to client {ip}")

    def update_child_uri(self):
        """Add incoming clients to the resource tree."""
        while len(ServerManager.incoming_queue_child_ips) > 0:
            ip = ServerManager.incoming_queue_child_ips.pop()

            if ip not in ServerManager.client_ip6:
                try:
                    # Allocate a resource to the client
                    self.allocate_resource(ip)
                    logging.info(
                        str(ip) + " updated in child sensitivity list with resource " + self.client_ip6[ip].uri
                        
                    )
                    ServerManager.pend_queue_child_ips.add(ip)
                    logging.info(str(ip) + " added to child pending queue")

                except KeyError:
                    logging.warning("Unable to update child sensitivity list with resource")
                    raise ValueError

    def update_child_device_info(self, ip: IPv6Address, csv: list):
        """ Updates the sensitivity list with new information from GasSentinel """
        try:
            if not isinstance(self.client_ip6[ip], OtGS):
                self.client_ip6[ip] = OtGS(device_type=OtDeviceType.GasSent, eui64=csv[4], temperature = csv[6],
                                           humidity=csv[7], pressure=csv[8], cl1=csv[9], cl2=csv[10], rssi= csv[11],
                                           vdd=csv[12])
            else:
                self.client_ip6[ip].eui64 = csv[4]
                self.client_ip6[ip].temperature = csv[6]
                self.client_ip6[ip].humidity = csv[7]
                self.client_ip6[ip].pressure = csv[8]
                self.client_ip6[ip].cl1 = csv[9]
                self.client_ip6[ip].cl2 = csv[10]
                self.client_ip6[ip].rssi = csv[11]
                self.client_ip6[ip].vdd = csv[12]
            self.client_ip6[ip].last_seen = time.time()

        except KeyError:
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError
