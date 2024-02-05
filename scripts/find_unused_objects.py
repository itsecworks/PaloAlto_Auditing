#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the unused objects with in panorama device-group hierarchy.
#
import xml.etree.ElementTree as ET
import time
import pdb

file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '7106.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'notused_objects_' + time_str + '.txt'


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

print("start time:", time.strftime("%Y%m%d_%H%M%S"))
result = ''

tree = ET.parse(xml_input)
root = tree.getroot()
ro_element = root.find("./readonly")
dg_parents = get_all_parents(ro_element)
print("load time:", time.strftime("%Y%m%d_%H%M%S"))

pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        print(dg_name)
        my_ch_list = []
        dg_all_child_names = get_all_children(dg_name, dg_parents, my_ch_list)

        addresses = dg.find("./address")
        post_rulebase = dg.find("./post-rulebase")
        pre_rulebase = dg.find("./pre-rulebase")
        address_groups = dg.find("./address-group")

        print("Lets remove the unused address-groups first, so we can remove addresses that were only in unused address-groups.")
        if address_groups is not None:
            for addr_grp in address_groups:
                addr_grp_name = addr_grp.attrib["name"]
                if pre_rulebase is None or (len(pre_rulebase) > 0 and addr_grp_name not in str(ET.tostring(pre_rulebase))):
                    if post_rulebase is None or (len(post_rulebase) > 0 and addr_grp_name not in str(ET.tostring(post_rulebase))):
                        if len(dg_all_child_names) > 0:
                            obj_used = False
                            for child_dg_name in dg_all_child_names:
                                child_dg = root.find("./devices/entry/device-group/entry[@name='" + child_dg_name + "']")
                                ch_post_rulebase = child_dg.find("./post-rulebase")
                                ch_pre_rulebase = child_dg.find("./pre-rulebase")
                                ch_address_groups = child_dg.find("./address-group")
                                if ch_pre_rulebase is not None and (len(ch_pre_rulebase) > 0 and addr_grp_name in str(ET.tostring(ch_pre_rulebase))):
                                    obj_used = True
                                    break
                                if ch_post_rulebase is not None and (len(ch_post_rulebase) > 0 and addr_grp_name in str(ET.tostring(ch_post_rulebase))):
                                    obj_used = True
                                    break
                                if ch_address_groups is not None and (len(ch_address_groups) > 0 and addr_grp_name in str(ET.tostring(ch_address_groups))):
                                    obj_used = True
                                    break
                            if not obj_used:
                                result += "{c1}, {c2}, {c3}\n".format(c1="address-group", c2=dg_name, c3=addr_grp_name)
                                if dg_name == "shared":
                                    xpath_remove = "./" + dg_name + "/address-group"
                                else:
                                    xpath_remove = "./devices/entry/device-group/entry[@name='" + dg_name + "']/address-group"
                                root.find(xpath_remove).remove(addr_grp)
                        else:
                            result += "{c1}, {c2}, {c3}\n".format(c1="address-group", c2=dg_name, c3=addr_grp_name)
                            if dg_name == "shared":
                                xpath_remove = "./" + dg_name + "/address-group"
                            else:
                                xpath_remove = "./devices/entry/device-group/entry[@name='" + dg_name + "']/address-group"
                            root.find(xpath_remove).remove(addr_grp)

        print("address check...")
        if addresses is not None:
            for addr in addresses:
                addr_name = addr.attrib["name"]
                if pre_rulebase is None or (len(pre_rulebase) > 0 and addr_name not in str(ET.tostring(pre_rulebase))):
                    if post_rulebase is None or (len(post_rulebase) > 0 and addr_name not in str(ET.tostring(post_rulebase))):
                        if address_groups is None or (len(address_groups) > 0 and addr_name not in str(ET.tostring(address_groups))):
                            if len(dg_all_child_names) > 0:
                                obj_used = False
                                for child_dg_name in dg_all_child_names:
                                    child_dg = root.find("./devices/entry/device-group/entry[@name='" + child_dg_name + "']")
                                    ch_post_rulebase = child_dg.find("./post-rulebase")
                                    ch_pre_rulebase = child_dg.find("./pre-rulebase")
                                    ch_address_groups = child_dg.find("./address-group")
                                    if ch_pre_rulebase is not None and (len(ch_pre_rulebase) > 0 and addr_name in str(ET.tostring(ch_pre_rulebase))):
                                        obj_used = True
                                        break
                                    if ch_post_rulebase is not None and (len(ch_post_rulebase) > 0 and addr_name in str(ET.tostring(ch_post_rulebase))):
                                        obj_used = True
                                        break
                                    if ch_address_groups is not None and (len(ch_address_groups) > 0 and addr_name in str(ET.tostring(ch_address_groups))):
                                        obj_used = True
                                        break
                                if not obj_used:
                                    result += "{c1}, {c2}, {c3}\n".format(c1="address", c2=dg_name, c3=addr_name)
                                    if dg_name == "shared":
                                        xpath_remove = "./" + dg_name + "/address"
                                    else:
                                        xpath_remove = "./devices/entry/device-group/entry[@name='" + dg_name + "']/address"
                                    root.find(xpath_remove).remove(addr)
                            else:
                                result += "{c1}, {c2}, {c3}\n".format(c1="address", c2=dg_name, c3=addr_name)
                                if dg_name == "shared":
                                    xpath_remove = "./" + dg_name + "/address"
                                else:
                                    xpath_remove = "./devices/entry/device-group/entry[@name='" + dg_name + "']/address"
                                root.find(xpath_remove).remove(addr)



with open(result_output, 'w') as fp:
    fp.write(result)

xml_str = ET.tostring(root)
with open(xml_output, 'wb') as f:
    f.write(xml_str)

print("end time:", time.strftime("%Y%m%d_%H%M%S"))