#!/usr/bin/python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import *
from ansible.module_utils.facts.utils import get_file_content, get_file_lines

import openshift

import os
import sys

from pprint import pprint

def get_memory_details():

  ORIGINAL_MEMORY_FACTS = frozenset(
        ("MemTotal", "SwapTotal", "MemFree", "SwapFree"))

  MEMORY_FACTS = ORIGINAL_MEMORY_FACTS.union(
        ("Buffers", "Cached", "SwapCached"))

    memory_details = {}
    if not os.access("/proc/meminfo", os.R_OK):
        return memory_details

    memstats = {}
    for line in get_file_lines("/proc/meminfo"):
        data = line.split(":", 1)
        key = data[0]
        if key in ORIGINAL_MEMORY_FACTS:
            val = data[1].strip().split(" ")[0]
            memory_details["%s_mb" % key.lower()] = int(val) // 1024

        if key in MEMORY_FACTS:
            val = data[1].strip().split(" ")[0]
            memstats[key.lower()] = int(val) // 1024

    if None not in (memstats.get("memtotal"), memstats.get("memfree")):
        memstats["real:used"] = memstats["memtotal"] - memstats["memfree"]
    if None not in (
            memstats.get("cached"),
            memstats.get("memfree"),
            memstats.get("buffers"),
    ):
        memstats["nocache:free"] = (memstats["cached"] + memstats["memfree"] +
                                    memstats["buffers"])
    if None not in (memstats.get("memtotal"), memstats.get("nocache:free")):
        memstats[
            "nocache:used"] = memstats["memtotal"] - memstats["nocache:free"]
    if None not in (memstats.get("swaptotal"), memstats.get("swapfree")):
        memstats["swap:used"] = memstats["swaptotal"] - memstats["swapfree"]

    memory_details["memory_mb"] = {
        "real": {
            "total": memstats.get("memtotal"),
            "used": memstats.get("real:used"),
            "free": memstats.get("memfree"),
        },
        "nocache": {
            "free": memstats.get("nocache:free"),
            "used": memstats.get("nocache:used"),
        },
        "swap": {
            "total": memstats.get("swaptotal"),
            "free": memstats.get("swapfree"),
            "used": memstats.get("swap:used"),
            "cached": memstats.get("swapcached"),
        },
    }

    return memory_details


def get_cpu_details():
    if not os.access("/proc/cpuinfo", os.R_OK):
        sys.exit(1)

    num_processor = 0
    sockets = {}
    cores = {}
    physid = 0
    cpu_details = {}
    cpu_details["processor"] = []
    idx = 0

    for line in get_file_lines("/proc/cpuinfo"):
        data = line.split(":", 1)
        key = data[0].strip()

        try:
            val = data[1].strip()
        except IndexError:
            val = ""

        if key in ["cpu", "processor", "model name", "vendor_id"]:
            if "processor" not in cpu_details:
                cpu_details["processor"] = []
            cpu_details["processor"].append(val)
            if key == "processor":
                num_processor += 1
            idx += 1

    return cpu_details


def get_node_stats():

from kubernetes import client, config
    from openshift.dynamic import DynamicClient

    k8s_client = config.new_client_from_config()
    dyn_client = DynamicClient(k8s_client)

    v1_nodes = dyn_client.resources.get(api_version="v1", kind="Node")

    node_list = v1_nodes.get()
    for node in node_list.items:
        if node["metadata"]["labels"][
                "node-role.kubernetes.io/infra"] == "true":
            pprint("capacity:::")
            pprint(node["status"]["capacity"])
            pprint("allocatable:::")
            pprint(node["status"]["allocatable"])


def main():
    module = AnsibleModule(argument_spec={})
    module.run_command_environ_update = {
        "LANG": "C",
        "LC_ALL": "C",
        "LC_NUMERIC": "C"
    }
    hardware_facts = {}

    cpu_details = get_cpu_details()
    memory_details = get_memory_details()

    hardware_facts.update(cpu_details)
    hardware_facts.update(memory_details)

    get_node_stats

    capacity = hardware_facts["memtotal_mb"] * 0.1
    system_reserved_mb = 1024
    allocatable = capacity - system_reserved_mb
    pprint("capacity: {} :: allocatable: {}".format(capacity, allocatable))

    module.exit_json(changed=False, meta=hardware_facts)


if __name__ == "__main__":
    main()
