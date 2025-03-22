# clustercron/alb.py
# vim: ts=4 et sw=4 sts=4 ft=python fenc=UTF-8 ai
# -*- coding: utf-8 -*-

"""
clustercron.alb
---------------

Modules holds class for AWS ElasticLoadBalancing v2 (ALB)
"""

from __future__ import unicode_literals

import logging

import boto3
from botocore.exceptions import NoRegionError

from .lb import Lb

logger = logging.getLogger(__name__)


class Alb(Lb):
    def _get_target_group_info(self):
        """Get target group information including ARN and target type"""
        target_group_info = {}
        try:
            client = boto3.client("elbv2")
        except NoRegionError as error:
            if self.region_name is None:
                logger.error("%s", error)
                return target_group_info
            else:
                client = boto3.client(
                    "elbv2",
                    region_name=self.region_name,
                )
        try:
            targetgroups = client.describe_target_groups(Names=[self.name])
        except client.exceptions.TargetGroupNotFoundException as error:
            logger.error(
                "Could not get TargetGroup `%s`: %s",
                self.name,
                error,
            )
        else:
            try:
                target_group = targetgroups.get("TargetGroups")[0]
                target_group_info["arn"] = target_group["TargetGroupArn"]
                target_group_info["type"] = target_group["TargetType"]
                logger.info("Target group type: %s", target_group_info["type"])
            except Exception as error:
                logger.error(
                    "Could not get TargetGroup info for `%s`: %s",
                    self.name,
                    error,
                )
        return target_group_info
        
    def _get_target_health(self):
        target_health = []
        logger.debug("Get target health states")
        target_group_info = self._get_target_group_info()
        
        if not target_group_info:
            return target_health
            
        try:
            client = boto3.client("elbv2")
        except NoRegionError as error:
            if self.region_name is None:
                logger.error("%s", error)
                return target_health
            else:
                client = boto3.client(
                    "elbv2",
                    region_name=self.region_name,
                )
                
        targetgroup_arn = target_group_info.get("arn")
        if not targetgroup_arn:
            return target_health
            
        logger.debug("targetgroup_arn: %s" % targetgroup_arn)
        try:
            target_health_response = client.describe_target_health(
                TargetGroupArn=targetgroup_arn
            )
            # Store target type with the health response
            target_health = {
                "TargetHealthDescriptions": target_health_response.get("TargetHealthDescriptions", []),
                "TargetType": target_group_info.get("type")
            }
        except Exception as error:
            logger.error("Could not get target health: %s", error)
            
        return target_health

    def get_healty_instances(self):
        healty_instances = []
        target_health = self._get_target_health()
        if target_health:
            logger.debug("Target health states: %s", target_health)
            try:
                healty_instances = sorted(
                    x["Target"]["Id"]
                    for x in target_health.get("TargetHealthDescriptions", [])
                    if x["TargetHealth"]["State"] == "healthy"
                )
            except Exception as error:
                logger.error("Could not parse healty_instances: %s", error)
            else:
                logger.info(
                    "Healty instances/IPs: %s", ", ".join(healty_instances)
                )
        return healty_instances
        
    def _is_master(self, healty_instances):
        """Determine if this instance is the master based on target type"""
        if not healty_instances:
            return False
            
        target_health = self._get_target_health()
        target_type = target_health.get("TargetType")
        
        logger.debug("Determining master with target type: %s", target_type)
        
        if target_type == "instance":
            # For instance-type targets, use instance ID
            if self.instance_id:
                return self.instance_id == healty_instances[0]
        elif target_type == "ip":
            # For IP-type targets, use eth0 IP
            if self.eth0_ip:
                return self.eth0_ip == healty_instances[0]
        else:
            logger.warning("Unknown target type: %s", target_type)
            
        return False
