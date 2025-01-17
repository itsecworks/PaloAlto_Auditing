#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the unused address-groups and addresses within panorama device-group hierarchy.
# It also checks fqdn address type if resolvable
# the code is bugy: addr-group in addr-group check is missing!!!
#
import xml.etree.ElementTree as ET
import time
import socket
import pdb

file_path = 'C:/temp/csaba/'
xml_input = file_path + 'config.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'paloalto_address_audit_' + time_str + '.csv'

def check_addr_rulebase(rulebase, obj_name):

    for ruletype in rulebase:
        for rule in ruletype.find('./rules/entry'):
            if rule.find('./source') is not None:
                if obj_name in str(ET.tostring(rule.find('./source'))):
                    print('objact name found')
            if rule.find('./destination') is not None:
                if obj_name in str(ET.tostring(rule.find('destination'))):
                    print('object name found')


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

    # we create a dictionary with key as the device-group and with value as a list of direct child device-groups.
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
result_csv = 'device-group, object_type, object_name, object_subtype, status\n'

tree = ET.parse(xml_input)
root = tree.getroot()
ro_element = root.find("./readonly")
dg_children = find_children(ro_element)
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
        pdb.set_trace()
        dg_descendants = find_descendants(dg_children, dg_name)
        addresses = dg.find("./address")
        post_rulebase = dg.find("./post-rulebase")
        pre_rulebase = dg.find("./pre-rulebase")
        address_groups = dg.find("./address-group")

        print("Lets remove the unused address-groups first, so we can remove addresses that were only in unused address-groups.")
        if address_groups is not None:
            for addr_grp in address_groups:
                addr_grp_name = addr_grp.attrib["name"]
                # addr-group in addr-group check is missing!!!
                if pre_rulebase is None or (len(pre_rulebase) > 0 and addr_grp_name not in str(ET.tostring(pre_rulebase))):
                    if post_rulebase is None or (len(post_rulebase) > 0 and addr_grp_name not in str(ET.tostring(post_rulebase))):
                        if len(dg_descendants) > 0:
                            obj_used = False
                            for child_dg_name in dg_descendants:
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
                                result_csv += "{c1}, {c2}, {c3}, {c4}, {c5}\n".format(c1=dg_name, c2="address-group", c3=addr_grp_name, c4="na", c5="not_used")
                                if dg_name == "shared":
                                    xpath_remove = "./" + dg_name + "/address-group"
                                else:
                                    xpath_remove = "./devices/entry/device-group/entry[@name='" + dg_name + "']/address-group"
                                root.find(xpath_remove).remove(addr_grp)
                        else:
                            result_csv += "{c1}, {c2}, {c3}, {c4}, {c5}\n".format(c1=dg_name, c2="address-group", c3=addr_grp_name, c4="na", c5="not_used")
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
                    addr_type = "fqdn"
                    addr_val = addr.find("fqdn").text
                    try:
                        data = socket.gethostbyname(addr_val)
                        result_csv += "{c1}, {c2}, {c3}, {c4} {c5}\n".format(c1=dg_name, c2="address", c3=addr_name, c4=addr_type, c5="resolvable")
                    except Exception:
                        # fail gracefully!
                        result_csv += "{c1}, {c2}, {c3}, {c4} {c5}\n".format(c1=dg_name, c2="address", c3=addr_name, c4=addr_type, c5="not-resolvable")
                elif addr.find("ip-netmask") is not None:
                    addr_type = "ip-netmask"
                elif addr.find("ip-range") is not None:
                    addr_type = "ip-range"
                else:
                    addr_type = "unknown"

                if pre_rulebase is None or (len(pre_rulebase) > 0 and addr_name not in str(ET.tostring(pre_rulebase))):
                    if post_rulebase is None or (len(post_rulebase) > 0 and addr_name not in str(ET.tostring(post_rulebase))):
                        if address_groups is None or (len(address_groups) > 0 and addr_name not in str(ET.tostring(address_groups))):
                            if len(dg_descendants) > 0:
                                obj_used = False
                                for child_dg_name in dg_descendants:
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
                                    result_csv += "{c1}, {c2}, {c3}, {c4}, {c5}\n".format(c1=dg_name, c2="address", c3=addr_name, c4=addr_type, c5="not_used")
                                    if dg_name == "shared":
                                        xpath_remove = "./" + dg_name + "/address"
                                    else:
                                        xpath_remove = "./devices/entry/device-group/entry[@name='" + dg_name + "']/address"
                                    root.find(xpath_remove).remove(addr)


                            else:
                                result_csv += "{c1}, {c2}, {c3}, {c4}, {c5}\n".format(c1=dg_name, c2="address", c3=addr_name, c4=addr_type, c5="not_used")
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
