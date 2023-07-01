import ipaddress
import time
import re
import logging
from aiocoap import resource,Message,CHANGED,BAD_REQUEST
import aiocoap

from server_sv_manager import ServerManager

class ResourceHandler(resource.Resource):
    """This resource supports the PUT methods.
    PUT: Update state of alarm."""

    def __init__(self, uri, sv_mgr: ServerManager):
        super().__init__()
        self.coap_payload = None
        self.path = uri
        self.sv_mgr = sv_mgr
        logging.info("Registered resource " + str(uri))

    async def render_put(self, request):
        """ Handles PUT requests, updates info, and calls functions to trigger actions. """
        client_ip = request.remote.hostinfo
        self.coap_payload = request.payload.decode("utf-8")
        csv = self.coap_payload.split(",")
        logging.info("Received PUT request from " + str(client_ip) + " with payload " + str(csv))
        logging.warning(csv)
        client_ip_str = str(re.sub(r"[\[\]]", "", client_ip))
        client_ip = ipaddress.ip_address(client_ip_str)
        
        # Check if CSV is valid. take in non-zero reading of inference cl1/cl2 
        if csv[5] == '0' or csv[6] == '0':
            logging.error("CSV contains zero value(s). Rejecting the request.")
            # Return an appropriate error response
            return aiocoap.Message(code=aiocoap.BAD_REQUEST)
            
        try:
            # Update the information on Client
            self.sv_mgr.update_child_device_info(client_ip, csv)
            # Check if response is None
            response = aiocoap.Message(code=aiocoap.CHANGED)
            return response

        except ValueError as e:
            logging.warning("Invalid payload: %s", str(e))
