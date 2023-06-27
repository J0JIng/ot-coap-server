import asyncio
from datetime import datetime
import logging
from influxdb_client import Point, WritePrecision
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from server_sv_manager import ServerManager, OtDeviceType


async def influx_task(sv_mgr: ServerManager):
    """Task to periodically send data to influxdb."""
    bucket = "00344c01ffe65fbb"
    org = "steal industry lpcs"
    token = "xY7YG1M7P5hAsilTNZfgE8ieMktqkU-BCD-Td7d7gLiO0fwLHvTREOTMXUdRLYfzFF_uabFwABofPCQ8zjbmsw=="
    # Store the URL of your InfluxDB instance
    url = "https://us-east-1-1.aws.cloud2.influxdata.com/orgs/c8f2e56a9bd8e1c9"
    async with InfluxDBClientAsync(url=url, token=token, org=org) as client:
        # set bucket
        while True:
            await asyncio.sleep(15)
            logging.info("Sent data to influxdb")
            # Create a data point for the OtDevice instance, and send it to the
            # InfluxDB server

            for ip in sv_mgr.get_all_child_ips():
                alive = sv_mgr.get_all_child_ips()[ip].last_seen > datetime.now().timestamp() - 30
                if sv_mgr.get_all_child_ips()[ip].device_type == OtDeviceType.GasSent:
                    point = (
                        Point("ot-ipr")
                        .tag("ip", ip)
                        .field("temperature", int(sv_mgr.get_all_child_ips()[ip].temperature))
                        .field("humidity", int(sv_mgr.get_all_child_ips()[ip].humidity))
                        .field("pressure", int(sv_mgr.get_all_child_ips()[ip].pressure))
                        .field("cl1", int(sv_mgr.get_all_child_ips()[ip].cl1))
                        .field("cl2", int(sv_mgr.get_all_child_ips()[ip].cl2))
                        .field("supply_vdd", int(sv_mgr.get_all_child_ips()[ip].vdd))
                        .field("rssi", int(sv_mgr.get_all_child_ips()[ip].rssi))
                        .field("alive", bool(alive))
                        .time(datetime.utcnow(), WritePrecision.MS)
                    )
                    # Write the data point to the database
                    try:
                        await client.write_api().write(bucket, org, point)
                    except (OSError, TimeoutError):
                        logging.error("Could not connect to influxdb")
                    except Exception as err:
                        logging.error("Could not write to influxdb")
                        logging.error(err)
                
