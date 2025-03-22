# clustercron/lb.py
# vim: ts=4 et sw=4 sts=4 ft=python fenc=UTF-8 ai
# -*- coding: utf-8 -*-

"""
clustercron.lb
---------------

Modules holds base class for AWS ElasticLoadBalancing classes
"""

from __future__ import unicode_literals

import logging

import boto.utils

logger = logging.getLogger(__name__)


class Lb(object):
    def __init__(self, name):
        """
        :param name: name of load balancer or target group
        """
        self.name = name
        self._get_instance_meta_data()

    def _get_instance_meta_data(self):
        try:
            data = boto.utils.get_instance_identity()
        except Exception as error:
            logger.error("Could not get instance data: %s", error)
            data = {"document": {}}
        self.region_name = data["document"].get("region")
        self.instance_id = data["document"].get("instanceId")
        
        # Get the eth0 IP address
        self.eth0_ip = self._get_eth0_ip()

        logger.info("self.region_name: %s", self.region_name)
        logger.info("self.instance_id: %s", self.instance_id)
        logger.info("self.eth0_ip: %s", self.eth0_ip)
        
    def _get_eth0_ip(self):
        """Get the IPv4 address of the eth0 interface"""
        try:
            # Try to get the IP using the 'ip' command
            result = subprocess.check_output(
                ["ip", "-4", "-o", "addr", "show", "dev", "eth0", "scope", "global"],
                universal_newlines=True
            )
            # Parse the output to extract the IP address
            if result:
                ip_parts = result.strip().split()
                for i, part in enumerate(ip_parts):
                    if part == "inet":
                        # Format is typically: inet 172.31.8.112/20 ...
                        return ip_parts[i+1].split("/")[0]
        except (subprocess.CalledProcessError, IndexError, FileNotFoundError) as error:
            logger.warning("Could not get eth0 IP using ip command: %s", error)
            
        # Fallback method using socket
        try:
            # Get all network interfaces
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        except Exception as error:
            logger.error("Could not get eth0 IP: %s", error)
            
        return None

    def get_healty_instances(self):
        raise NotImplementedError

    def master(self):
        logger.debug("Check if instance is master")
        if self.instance_id is None and self.eth0_ip is None:
            logger.error("No Instance Id or IP address available")
            return False
            
        healty_instances = self.get_healty_instances()
        if not healty_instances:
            return False
            
        # The actual comparison logic is implemented in the subclasses
        # that know whether to use instance_id or eth0_ip
        return self._is_master(healty_instances)
        
    def _is_master(self, healty_instances):
        """Determine if this instance is the master based on healthy instances"""
        # Default implementation uses instance_id
        return self.instance_id == healty_instances[0]
