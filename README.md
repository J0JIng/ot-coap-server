# ot-coap-server for [GasSentinel]()

This repo contains a python script to provide a CoAP server.

The server advertises it's service and allocates a common resource to the clients connected to the OpenThread network.

CoAP messages are sent in CSV format, where the entries are as specified in the code.

Running server_main.py will do the following tasks:

1) Start a CoAP server on port 5683, and bind to wpan0 i/f on mesh local address. 
2) Start ServerManager, pass the ipv6 of the server as the argument to the constructor.
3) Start a task to post data to influxDB.
