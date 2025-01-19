#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the used fqdn objects in all panorama device-group hierarchies.
#
import xml.etree.ElementTree as ET
import time
import socket
import json

file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '12257.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'notused_objects_' + time_str + '.txt'


# Function to find all descendants fora a device-group recursively
def find_descendants(dg_children, parent_dg):
    
    dg_descendants = []  # List to store descendants of a device-group
    # Find all children of the given parent
    if parent_dg in dg_children:
        children = dg_children[parent_dg]
    
        for child in children:
            # add a single list element to the descendant list
            dg_descendants.append(child)
            # extend with multiple list elements the device-group with recursively get descendants
            dg_descendants.extend(find_descendants(dg_children, child)) 
    
    return dg_descendants


# Function to find all children to each device-group
def find_children(ro_element):

    # we create a dictionary with key as the device-group and with value as a list of direct child device-groups
    dg_children = {}
    dg_children['shared'] = []
    for dg in ro_element.findall('./devices/entry/device-group/entry'):
        dg_name = dg.get('name')
        if dg.find('./parent-dg') is not None and len(dg.find('./parent-dg').text) > 0:
            parent_dg_name = dg.find('./parent-dg').text
        else:
            parent_dg_name = 'shared'
            
        if parent_dg_name not in dg_children:
            dg_children[parent_dg_name] = [dg_name]
        else:
            dg_children[parent_dg_name].append(dg_name)

    return (dg_children)

print("start time:", time.strftime("%Y%m%d_%H%M%S"))
result = ''

tree = ET.parse(xml_input)
root = tree.getroot()
ro_element = root.find("./readonly")
dg_children = find_children(ro_element)
print("load time:", time.strftime("%Y%m%d_%H%M%S"))

fqdn_count = {}

pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        print(dg_name)
        if dg_name not in fqdn_count:
            fqdn_count[dg_name] = {}
        my_ch_list = []
        dg_descendants = find_descendants(dg_children, dg_name)
        addresses = dg.find("./address")
        post_rulebase = dg.find("./post-rulebase")
        pre_rulebase = dg.find("./pre-rulebase")
        address_groups = dg.find("./address-group")

        print("address-group check...")
        print("Lets remove the unused address-groups first, so we can remove addresses that were only in unused address-groups.")
        if address_groups is not None:
            for addr_grp in address_groups:
                addr_grp_name = addr_grp.attrib["name"]
                # addr-group in addr-group check is missing!!!
                #print(dg_name, addr_grp_name)
                #print(dg_name, addr_grp_name, "pre-rules")
                if pre_rulebase is None or (len(pre_rulebase) > 0 and addr_grp_name not in str(ET.tostring(pre_rulebase))):
                    #print(dg_name, addr_grp_name, "post-rules")
                    if post_rulebase is None or (len(post_rulebase) > 0 and addr_grp_name not in str(ET.tostring(post_rulebase))):
                        if len(dg_descendants) > 0:
                            obj_used = False
                            for child_dg_name in dg_descendants:
                                child_dg = root.find("./devices/entry/device-group/entry[@name='" + child_dg_name + "']")
                                ch_post_rulebase = child_dg.find("./post-rulebase")
                                ch_pre_rulebase = child_dg.find("./pre-rulebase")
                                ch_address_groups = child_dg.find("./address-group")
                                #print("child dg: ", child_dg_name, addr_grp_name, "pre-rules")
                                if ch_pre_rulebase is not None and (len(ch_pre_rulebase) > 0 and addr_grp_name in str(ET.tostring(ch_pre_rulebase))):
                                    obj_used = True
                                    break
                                #print("child dg: ", child_dg_name, addr_grp_name, "post-rules")
                                if ch_post_rulebase is not None and (len(ch_post_rulebase) > 0 and addr_grp_name in str(ET.tostring(ch_post_rulebase))):
                                    obj_used = True
                                    break
                                #print("child dg: ", child_dg_name, addr_grp_name, "address-groups")
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
                if addr.find("fqdn") is not None:
                    #print("dg: ", dg_name, addr_name)
                    addr_type = "fqdn"
                    addr_val = addr.find("fqdn").text
                    try:
                        data = socket.gethostbyname(addr_val)
                        result += "{c1}, {c2}, {c3}, {c4} {c5}\n".format(c1="address", c2=dg_name, c3=addr_name, c4=addr_type, c5="resolvable")
                    except Exception:
                        # fail gracefully!
                        result += "{c1}, {c2}, {c3}, {c4} {c5}\n".format(c1="address", c2=dg_name, c3=addr_name, c4=addr_type, c5="not-resolvable")
                    if pre_rulebase is not None and (len(pre_rulebase) > 0 and addr_name in str(ET.tostring(pre_rulebase))):
                        #print("dg: ", dg_name, addr_name, " pre-rules")
                        # count it
                        fqdn_count[dg_name][addr_name] = 1
                    elif post_rulebase is not None and (len(post_rulebase) > 0 and addr_name in str(ET.tostring(post_rulebase))):
                        #print("dg: ", dg_name, addr_name, " post-rules")
                        # count it
                        fqdn_count[dg_name][addr_name] = 1
                    elif address_groups is not None and (len(address_groups) > 0 and addr_name in str(ET.tostring(address_groups))):
                        #print("dg: ", dg_name, addr_name, " address-groups")
                        # count it
                        fqdn_count[dg_name][addr_name] = 1
                    if len(dg_descendants) > 0:
                        for child_dg_name in dg_descendants:
                            #print("child dg: ", child_dg_name)
                            if child_dg_name not in fqdn_count:
                                fqdn_count[child_dg_name] = {}
                            child_dg = root.find("./devices/entry/device-group/entry[@name='" + child_dg_name + "']")
                            ch_post_rulebase = child_dg.find("./post-rulebase")
                            ch_pre_rulebase = child_dg.find("./pre-rulebase")
                            ch_address_groups = child_dg.find("./address-group")
                            if ch_pre_rulebase is not None and (len(ch_pre_rulebase) > 0 and addr_name in str(ET.tostring(ch_pre_rulebase))):
                                print("child dg: ", child_dg_name, addr_name, "pre-rules")
                                # count it
                                fqdn_count[child_dg_name][addr_name] = 1
                            elif ch_post_rulebase is not None and (len(ch_post_rulebase) > 0 and addr_name in str(ET.tostring(ch_post_rulebase))):
                                #print("child dg: ", child_dg_name, addr_name, "post-rules")
                                # count it
                                fqdn_count[child_dg_name][addr_name] = 1

                            elif ch_address_groups is not None and (len(ch_address_groups) > 0 and addr_name in str(ET.tostring(ch_address_groups))):
                                #print("child dg: ", child_dg_name, addr_name, "address-groups")
                                # count it
                                fqdn_count[child_dg_name][addr_name] = 1


for dg_name in fqdn_count:
    print(dg_name, " : ", len(fqdn_count[dg_name]))

json_string = json.dumps(fqdn_count,
                         allow_nan=True,
                         indent=6)

print(json_string)

with open(result_output, 'w') as fp:
    fp.write(result)
    fp.write("------------------------------------------------------------------------------------------------")
    for dg_name in fqdn_count:
        line = dg_name + " : " + str(len(fqdn_count[dg_name])) + "\n"
        fp.write(line)
    fp.write("------------------------------------------------------------------------------------------------")
    fp.write(json_string)

xml_str = ET.tostring(root)
with open(xml_output, 'wb') as f:
    f.write(xml_str)

print("end time:", time.strftime("%Y%m%d_%H%M%S"))
