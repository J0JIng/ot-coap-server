# ot-coap-server for [GasSentinel](https://github.com/J0JIng/GasSentinel)

This repo contains a python script to provide a CoAP server.

The server advertises it's service and allocates a common resource to the clients connected to the OpenThread network.

CoAP messages are sent in CSV format, where the entries are as specified in the code.

Running server_main.py will do the following tasks:
1) Start a CoAP server on port 5683, and bind to wpan0 i/f on mesh local address. using the IPv6 address of the host machine and creates a resource tree.
2) An instance of the ServerManager class is created to manage the server and handle client interactions by passing the ipv6 of the server as the argument to the constructor.
3) The server advertises its presence and adds a common resource to the resource tree. Allowing the clients to identify and connect to the server.
4) The main task, server context, advertising task, and an InfluxDB sender task are executed within an event loop, allowing the server to handle client requests, advertise itself, and send data to InfluxDB.
