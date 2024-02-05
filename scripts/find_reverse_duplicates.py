#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Author: Ist wurst...
#
# Description:
# -------------
# This script finds the reverse duplicates like:
#               /-h_9.9.9.9
#IP:9.9.9.9\32 =
#               \-h_quadnine
#
# people tend to recreate objects that exists already with a new name...
#
import xml.etree.ElementTree as ET
import time


file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '7106.xml'
#xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'reverse_duplicate_objects_' + time_str + '.csv'

tree = ET.parse(xml_input)
root = tree.getroot()

addr_dict = {}

pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}

for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        for address in dg.findall("./address/entry"):
            for element in address:
                if element.tag in ["ip-netmask", "fqdn", "ip-range"]:
                    if dg_name not in addr_dict:
                        addr_dict[dg_name] = {}
                    if element.text not in addr_dict[dg_name]:
                        addr_dict[dg_name][element.text] = {}
                        addr_dict[dg_name][element.text]["type"] = element.tag
                        addr_dict[dg_name][element.text]["objects"] = [address.attrib["name"]]
                    else:
                        addr_dict[dg_name][element.text]["objects"].append(address.attrib["name"])

result = ''
for dg in addr_dict:
    mcounter = {}
    nuc = 0
    uc = 0
    for obj_val in addr_dict[dg]:
        if len(addr_dict[dg][obj_val]["objects"]) > 1:
            for obj in addr_dict[dg][obj_val]["objects"]:
                result += "{c1}, {c2}, {c3}, {c4}\n".format(c1=dg,
                                                            c2=str(obj_val),
                                                            c3=addr_dict[dg][obj_val]["type"],
                                                            c4=str(obj))
            nuc += 1
            obj_count = len(addr_dict[dg][obj_val]["objects"])
            if obj_count not in mcounter:
                mcounter[obj_count] = 1
            else:
                mcounter[obj_count] += 1
        else:
            uc += 1

    print("unique-nonu-counts," + dg + "," + str(uc) + "," + str(nuc))

    for obj_count in mcounter:
        print("multiplied," + dg + "," + str(obj_count) + "," + str(mcounter[obj_count]))

with open(result_output, 'w') as fp1:
    fp1.write(result)