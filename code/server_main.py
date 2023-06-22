import asyncio  # pylint: disable=import-error
import ipaddress
import logging
import coloredlogs

# CoAP lib / Network
import aiocoap
from aiocoap import resource
import aiocoap.numbers.constants
import netifaces

# imported modules
#import influx_sender
from server_sv_manager import ServerManager
from server_resource_handler import ResourceHandler

# Declaring Global Variable
START_TASK_INFLUX_SENDER = False
POLL_NEW_CHILDREN_INTERVAL_S = 30

# Change accordingly to machine
COAP_UDP_DEFAULT_PORT = 5683
OT_DEFAULT_PREFIX = "fd62"
OT_DEFAULT_IFACE = "wpan0"

def get_ipv6_address():
    """
    Get the IPv6 address of a specific network interface with a given address prefix.
    Returns None if no matching address is found.
    """

    addrs = netifaces.ifaddresses(OT_DEFAULT_IFACE)
    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        if i["addr"].startswith(OT_DEFAULT_PREFIX):
            break
        ctr +=1

    if ctr < len(addrs[netifaces.AF_INET6]):
        return ipaddress.ip_address(addrs[netifaces.AF_INET6][ctr]["addr"])
    else:
        return None


def main(root_res: resource.Site):
    """Main function that starts the server"""
    # Resource tree creation
    server_ipv6_address = get_ipv6_address(OT_DEFAULT_IFACE,OT_DEFAULT_PREFIX)
    if server_ipv6_address:
        logging.info(f"Server running. IPv6 address: {server_ipv6_address}")
    else:
        logging.error("Failed to retrieve IPv6 address")
     # create an instance of ServerManager() class
    sv_mgr = ServerManager(ipaddress.ip_address(server_ipv6_address))
    # Get event loop
    loop = asyncio.get_event_loop()
    # Create the server context task
    coap_context = loop.create_task(
        aiocoap.Context.create_server_context(
            root_res , bind = ( server_ipv6_address, COAP_UDP_DEFAULT_PORT)
        )
    )
    logging.info("Server running")
    # Start the advertising service task
    advertising_task = loop.create_task(sv_mgr.DNS_register_service(COAP_UDP_DEFAULT_PORT)) # Advertise server via DNS-SD
    logging.info("Advertising Server...")
    

    try:
        # Wait for the server context, advertising tasks and main_task to complete
        await asyncio.gather(coap_context, advertising_task, main_task, 
                             #influx_sender if True else None
                            )
    except KeyboardInterrupt:
        # Handle keyboard interrupt
        logging.info("Keyboard interrupt detected. Stopping server...")
        # Cancel the advertising task
        advertising_task.cancel()
        try:
            # Wait for the advertising task to be cancelled
            await advertising_task
        except asyncio.CancelledError:
            pass

        # Stop the event loop
        loop.stop()


async def main_task(sv_manager: ServerManager, root_res: resource.Site):
    """Add clients to resource tree"""
    while True:
        logging.info("inviting new children...")
        ip = sv_manager.pend_queue_res_child_ips.pop()
        while ip is not None:
            try:
                root_res.add_resource(
                    (sv_manager.get_all_child_ips()[ip].uri,),
                    ResourceHandler(sv_manager.get_all_child_ips()[ip].uri, sv_manager),
                )
                logging.info(
                    "Added new child " + str(ip) + " with resource " + sv_manager.get_all_child_ips()[ip].uri
                )
            except KeyError:
                logging.info("Child " + str(ip) + " error")
                pass

        await asyncio.sleep(POLL_NEW_CHILDREN_INTERVAL_S)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    coloredlogs.install(level="INFO")

    coap_root = resource.Site()
    logging.info("Startup success")
    try:
        main(coap_root)
    except KeyboardInterrupt:
        logging.error("Exiting")
