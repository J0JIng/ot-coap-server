# Helper lib
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
import influx_sender
from server_sv_manager import ServerManager
from server_resource_handler import ResourceHandler

# Declaring Global Variable
POLL_NEW_CHILDREN_INTERVAL_S = 30

# Change accordingly to machine
COAP_UDP_DEFAULT_PORT = 5683
OT_DEFAULT_PREFIX = ""
OT_DEFAULT_IFACE = "wpan0"


def get_ipv6_address():
    """ Get the IPv6 address of a specific network interface with a given address prefix.
    Returns None if no matching address is found. """
    addrs = netifaces.ifaddresses(OT_DEFAULT_IFACE)
    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        if i["addr"].startswith(OT_DEFAULT_PREFIX):
            break
        ctr += 1

    if ctr < len(addrs[netifaces.AF_INET6]):
        return ipaddress.ip_address(addrs[netifaces.AF_INET6][ctr]["addr"])
    else:
        return None


async def main_task(sv_manager: ServerManager, root_res: resource.Site):
    """ Add clients to resource tree. """
    while True:
        logging.info("inviting new children...")
        while sv_manager.pend_queue_child_ips:
            ip = sv_manager.pend_queue_child_ips.pop()
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


def main(root_res: resource.Site):
    """ Main function that starts the server. """
    # Resource tree creation
    server_ipv6_address = get_ipv6_address()
    if server_ipv6_address:
        logging.info(f"Server running. IPv6 address: {server_ipv6_address}")
    else:
        logging.error("Failed to retrieve IPv6 address")
        
    sv_mgr = ServerManager(ipaddress.ip_address(server_ipv6_address))  # create an instance of ServerManager() class
    loop = asyncio.new_event_loop()  # Get event loop
    asyncio.set_event_loop(loop)
    
    # Create the server context task
    coap_context = loop.create_task(
        aiocoap.Context.create_server_context(
            root_res, bind=(str(server_ipv6_address), COAP_UDP_DEFAULT_PORT)
        )
    )
    logging.info("Server running")
    
    # Start the advertising service task
    advertising_task = loop.create_task(sv_mgr.advertise_server())  # Advertise server
    logging.info("Advertising Server...")
    root_res.add_resource( ("common",), ResourceHandler("common",sv_mgr),)
    
    # Create the main task
    main_tasks = loop.create_task(main_task(sv_mgr, root_res))
   
    try:
        # Wait for the server context, advertising tasks and main_task to complete
        loop.run_until_complete( asyncio.gather(coap_context, advertising_task, main_tasks,
                                               influx_sender.influx_task(sv_mgr)))
    except KeyboardInterrupt:
        # Handle keyboard interrupt
        logging.info("Keyboard interrupt detected. Stopping server...")
        # Stop the event loop
        loop.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    coloredlogs.install(level="INFO")

    coap_root = resource.Site()
    logging.info("Startup success")
    try:
        main(coap_root)
    except KeyboardInterrupt:
        logging.error("Exiting")
