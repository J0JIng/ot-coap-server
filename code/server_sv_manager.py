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
    common_resource_uri = "common" # Common Resource for URL

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
        """Allocate a common resource to the client."""
        self.client_ip6[ip].uri = self.common_resource_uri
        
    def update_child_uri(self):
        """Add incoming clients to the resource tree."""
        while len(self.incoming_queue_child_ips) > 0:
            ip = self.incoming_queue_child_ips.pop()

            if ip in self.client_ip6:
                # Allocate a resource to the client
                    self.allocate_resource(ip)
                    logging.info(
                        str(ip) + " updated in child sensitivity list with resource " + self.client_ip6[ip].uri
                        
                    )
                    ServerManager.pend_queue_child_ips.add(ip)
                    logging.info(str(ip) + " added to child pending queue")
            else:
                logging.warning("Unable to update child sensitivity list with resource for IP " + str(ip))

            

    def update_child_device_info(self, ip: IPv6Address, csv: list):
        """Updates the sensitivity list with new information from GasSentinel"""

        # Check if the child IP is already present in the sensitivity list
        if ip in self.client_ip6:
            # Update the existing child device with the new information
            child_device = self.client_ip6[ip]
            child_device.eui64 = csv[4]
            child_device.temperature = csv[6]
            child_device.humidity = csv[7]
            child_device.pressure = csv[8]
            child_device.cl1 = csv[9]
            child_device.cl2 = csv[10]
            child_device.rssi = csv[11]
            child_device.vdd = csv[12]
            child_device.last_seen = time.time()
            
        else:
            # Create a new child device and add it to the sensitivity list
            new_child_device = OtGS(
                device_type=OtDeviceType.GasSent,
                eui64=csv[4],
                temperature=csv[6],
                humidity=csv[7],
                pressure=csv[8],
                cl1=csv[9],
                cl2=csv[10],
                rssi=csv[11],
                vdd=csv[12]
            )
            new_child_device.last_seen = time.time()
            # Add the child IP to the sensitivity list
            self.client_ip6[ip] = new_child_device
            # Place the child IP into the incoming queue to be added into the resource tree
            self.incoming_queue_child_ips.add(ip)
            # Update the resource tree with client information
            self.update_child_uri()
            logging.info(str(ip) + " added to incoming queue " + new_child_device.uri)
            
