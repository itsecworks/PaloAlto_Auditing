#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script finds rules with too large network address abd the objects using them mask and finds the rules where they all are used.
#
import xml.etree.ElementTree as ET
import time

file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '7106.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'address_objects_with_large_netmask_' + time_str + '.csv'
netmask_limit = 16


def get_rules(obj_name, rulebase_xml):


    rules_lst = []
    for rule_type in rulebase_xml:
        if rule_type.findall("./rules/entry") is not None:
            for rule in rule_type.findall("./rules/entry"):
                for entry in ["source", "destination"]:
                    if rule.find("./" + entry) is not None:
                        data = rule.find("./" + entry)
                        if obj_name in str(ET.tostring(data)):
                            rules_lst.append(rule_type.tag + " - " + rule.attrib["name"])

    return rules_lst


def get_address_groups(addr_grps, addr_name, match_list=None):


    if match_list is None:
        match_list = []
    for addr_grp in addr_grps.findall("./entry"):
        if addr_grp.findall("./static/member") is not None:
            for member in addr_grp.findall("./static/member"):
                if addr_name in member.text:
                    new_name = addr_grp.attrib["name"]
                    match_list.append(new_name)
                    return get_address_groups(addr_grps, new_name, match_list)
    return match_list


def get_all_children(dg_name, dg_parents, dg_child_list):


    if dg_name in dg_parents:
        dg_child_list += dg_parents[dg_name]
        if dg_name != "shared":
            for child_dg in dg_parents[dg_name]:
                get_all_children(child_dg, dg_parents, dg_child_list)
    return dg_child_list


def get_all_parents(ro_element):

    # a dictionary with key as a parent dg and value as all dg that parent dg is the one in the key.
    dg_parents = {}
    dg_parents["shared"] = []
    for dg in ro_element.findall("./devices/entry/device-group/entry"):
        dg_name = dg.attrib["name"]
        dg_parents["shared"].append(dg_name)
        if dg.find("./parent-dg") is not None:
            parent_dg_name = dg.find("./parent-dg").text
            if parent_dg_name not in dg_parents:
                dg_parents[parent_dg_name] = [dg_name]
            else:
                dg_parents[parent_dg_name].append(dg_name)

    return (dg_parents)


tree = ET.parse(xml_input)
root = tree.getroot()
ro_element = root.find("./readonly")
dg_parents = get_all_parents(ro_element)
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
result = {}

for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        my_ch_list = []
        dg_all_child_names = get_all_children(dg_name, dg_parents, my_ch_list)
        addresses = dg.find("./address")
        address_groups = dg.find("./address-group")

        if addresses is not None:
            for addr in addresses:
                used_objects = []
                addr_name: str = addr.attrib["name"]
                if addr.find("./ip-netmask") is not None:
                    ip = addr.find("./ip-netmask").text
                    if "/" in ip:
                        netmask = ip.split("/")[1]
                        if int(netmask) < netmask_limit:
                            print("unaccepted nw object:", dg_name, addr_name, " with netmask: ", netmask)
                            if dg_name not in result:
                                result[dg_name] = {}
                            if addr_name not in result[dg_name]:
                                result[dg_name][addr_name] = {}
                                result[dg_name][addr_name]["netmask"] = netmask
                                result[dg_name][addr_name]['used_objects'] = [addr_name]

                            if address_groups is not None and len(address_groups) > 0 and addr_name in str(ET.tostring(address_groups)):
                                used_objects = get_address_groups(address_groups, addr_name)
                                result[dg_name][addr_name]['used_objects'] += used_objects

                            for object in result[dg_name][addr_name]['used_objects']:
                                for rule_pos in ["pre-rulebase", "post-rulebase"]:
                                    data = dg.find("./" + rule_pos)
                                    if data is not None and len(data) > 0 and object in str(ET.tostring(data)):
                                        if rule_pos not in result[dg_name][addr_name]:
                                            result[dg_name][addr_name][rule_pos] = get_rules(object, data)
                                        else:
                                            result[dg_name][addr_name][rule_pos] += get_rules(object, data)

                            if len(dg_all_child_names) > 0:
                                for child_dg_name in dg_all_child_names:
                                    used_objects_new = []
                                    child_dg = root.find("./devices/entry/device-group/entry[@name='" + child_dg_name + "']")
                                    ch_address_groups = child_dg.find("./address-group")
                                    if ch_address_groups is not None and len(ch_address_groups) > 0 and addr_name in str(ET.tostring(ch_address_groups)):
                                        if len(used_objects) > 0:
                                            for entry in used_objects:
                                                used_objects_new += get_address_groups(ch_address_groups, entry)
                                        else:
                                            used_objects_new = get_address_groups(ch_address_groups, addr_name)

                                        result[dg_name][addr_name]['used_objects'] += used_objects_new
                                        used_objects += used_objects_new

                                    for object in result[dg_name][addr_name]['used_objects']:
                                        for rule_pos in ["pre-rulebase", "post-rulebase"]:
                                            data = child_dg.find("./" + rule_pos)
                                            if data is not None and len(data) > 0 and object in str(ET.tostring(data)):
                                                if rule_pos not in result[dg_name][addr_name]:
                                                    result[dg_name][addr_name][rule_pos] = get_rules(object, data)
                                                else:
                                                    result[dg_name][addr_name][rule_pos] += get_rules(object, data)

#write to csv output
result_csv = ''
for dg_name in result:
    for addr_name in result[dg_name]:
        for key in result[dg_name][addr_name]:
            if isinstance(result[dg_name][addr_name][key],list):
                for entry in result[dg_name][addr_name][key]:
                    result_csv += "{c1}, {c2}, {c3}, {c4}\n".format(c1=dg_name, c2=addr_name, c3=key, c4=entry)
            else:
                result_csv += "{c1}, {c2}, {c3}, {c4}\n".format(c1=dg_name, c2=addr_name, c3=key,
                                                                c4=result[dg_name][addr_name][key])

with open(result_output, 'w') as fp:
    fp.write(result_csv)