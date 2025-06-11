#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the inherited objects within panorama device-group hierarchy 
# when you copy a complete device-group hierarchy
# fields checked:
# -----------------
# address (src, dst)
# service
# applications

import sys
import xml.etree.ElementTree as ET
import time
import pdb


# Function to find all ancestors for a device-group recursively
def find_ancestors(ro_element, child_dg):

    if "shared" in child_dg:
        return []

    dg = ro_element.find("./devices/entry/device-group/entry[@name='" + child_dg + "']")
    dg_parent = dg.find('./parent-dg')
    if dg_parent is not None and len(dg_parent.text) > 0:
        parent_dg = dg.find('./parent-dg').text
        # Recursively collect ancestors from the parent
        ancestors = find_ancestors(ro_element, parent_dg)
        # Add the current parent to the list of ancestors
        ancestors.append(parent_dg)
        return ancestors

    # Base case: If there is no parent (None or no text in tag parent-dg), return 'shared'
    else:
        return ['shared']


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

    return dg_children


def resolve_group(dg_data, dg_name, group_name, visited=None):
    if visited is None:
        visited = set()
    result = []

    def helper(dg_name, group_name):
        if (dg_name, group_name) in visited:
            return
        visited.add((dg_name, group_name))

        group_items = dg_data.get(dg_name, {}).get("address-group", {}).get(group_name, [])
        #print(group_items)
        for item in group_items:
            # First check if it's a direct address in this DG
            if item in dg_data[dg_name].get("address", []):
                result.append(item)
            # Then check if it's another group in this DG
            elif item in dg_data[dg_name].get("address-group", {}):
                helper(dg_name, item)
            else:
                # Not found in current DG, check ancestors
                for ancestor in dg_data[dg_name].get("ancestors", []):
                    if item in dg_data[ancestor].get("address", []):
                        result.append(item)
                        break
                    elif item in dg_data[ancestor].get("address-group", {}):
                        helper(ancestor, item)
                        break

    helper(dg_name, group_name)
    return result


def get_object_names(dg, obj_type):

    if 'group' in obj_type:
        obj_list = {}
    else:
        obj_list = set()

    if 'fqdn' in obj_type:
        obj_xpath = './address/entry'
    else:
        obj_xpath = './' + obj_type + '/entry'

    objects_xml = dg.findall(obj_xpath)
    if objects_xml is not None:
        for entry in objects_xml:
            obj_name = entry.get("name")
            if 'group' in obj_type:
                if "address-group" in obj_type:
                    obj_items_xpath = "./static/member"
                else:
                    obj_items_xpath = "./members/member"
                obj_list[obj_name] = set()
                members = entry.findall(obj_items_xpath)
                if members is not None:
                    for member in members:
                        obj_list[obj_name].add(member.text)
            elif 'fqdn' in obj_type and entry.find("fqdn") is not None:
                obj_list.add(obj_name)
            else:
                obj_list.add(obj_name)

    return obj_list


def get_members(xml_element, xpath):

    member_list = set()
    xml_elements = xml_element.findall(xpath)
    if xml_elements is not None:
        for member in xml_elements:
            member_list.add(member.text)
    return member_list


def get_rule_object_names(dg):

    rule_objects = {}
    rule_positions = ["pre-rulebase", "post-rulebase"]
    rule_objects["rulebase-addr"] = set()
    rule_objects["rulebase-svc"] = set()
    rule_objects["rulebase-app"] = set()
    for rule_position in rule_positions:
        rb_xpath = "./" + rule_position
        rulebase_xml = dg.find(rb_xpath)
        if rulebase_xml is not None:
            for rule_type_xml in rulebase_xml:
                rules_xml = rule_type_xml.findall('./rules/entry')
                if rules_xml is not None:
                    for rule in rules_xml:
                        # rulebase address objects
                        address_locations = ["source", "destination"]
                        for addr_location in address_locations:
                            rule_addr_xpath = './' + addr_location + '/member'
                            rule_objects["rulebase-addr"].update(get_members(rule, rule_addr_xpath))
                        # rulebase services
                        rule_svc_xpath = './service/member'
                        rule_objects["rulebase-svc"].update(get_members(rule, rule_svc_xpath))
                        # rulebase applications
                        rule_app_xpath = './application/member'
                        rule_objects["rulebase-app"].update(get_members(rule, rule_app_xpath))

    return rule_objects


def collect_dg_data(xml_root, ro_element):

    dg_children = find_children(ro_element)
    dg_objects = {}

    pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
    for key in pa_all_dgs:
        xpath = pa_all_dgs[key]
        for dg in xml_root.findall(xpath):
            if key == "default":
                dg_name = dg.attrib["name"]
            else:
                dg_name = key
            print("loading up to dg_data for ", dg_name)
            dg_objects[dg_name] = {}
            dg_objects[dg_name]["descendants"] = find_descendants(dg_children, dg_name)
            dg_objects[dg_name]["ancestors"] = find_ancestors(ro_element, dg_name)
            obj_types = ["fqdn", "address", "address-group", "service", "service-group", "application-group", "application"]

            for obj_type in obj_types:
                dg_objects[dg_name][obj_type] = get_object_names(dg, obj_type)

            rule_objects = get_rule_object_names(dg)
            dg_objects[dg_name].update(rule_objects)

    return dg_objects


def get_device_groups_xml(element_root):
    # load the device-group Elements to a dictionary to get needed objects
    dg_xml = {}
    pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
    for key in pa_all_dgs:
        xpath = pa_all_dgs[key]
        for dg in element_root.findall(xpath):
            if key == "default":
                dg_name = dg.attrib["name"]
            else:
                dg_name = key
            dg_xml[dg_name] = dg

    return dg_xml


def main(argv):

    print("script start timestamp : ", time.strftime("%Y%m%d_%H%M%S"))
    dg_name_to_copy = "DEBERPMIFW11-12"
    file_path = 'C:/Users/dakos/Downloads/'
    xml_input_old = file_path + '14185.xml'
    xml_input_new = file_path + 'running-config_202505052300.xml'

    time_str = time.strftime("%Y%m%d_%H%M%S")
    result_output = file_path + 'paloalto_dg_copy_' + time_str + '.xml'

    element_tree_old = ET.parse(xml_input_old)
    element_root_old = element_tree_old.getroot()
    ro_element_old = element_root_old.find("./readonly")

    element_tree_new = ET.parse(xml_input_new)
    element_root_new = element_tree_new.getroot()
    ro_element_new = element_root_new.find("./readonly")

    print("xml loaded timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    dg_data_old = collect_dg_data(element_root_old, ro_element_old)
    dg_data_new = collect_dg_data(element_root_new, ro_element_new)
    print("time after dictionary created : ", time.strftime("%Y%m%d_%H%M%S"))

    # build the dependencies for device-group to extract from running configuration
    f = open(result_output, "x")

    ancestors_to_copy = []
    ancestors_to_copy.extend(dg_data_old[dg_name_to_copy]["ancestors"])
    ancestors_to_copy.append(dg_name_to_copy)
    # list_reverse_iterator object
    reversed_ancestors_to_copy = reversed(ancestors_to_copy)
    # should be converted back to list
    reversed_ancestors_list_to_copy = list(reversed_ancestors_to_copy)
    print("device-group hierarchy: ", reversed_ancestors_list_to_copy)

    # load the device-group Elements to a dictionary to get needed objects
    dgs_xml_dict_old = get_device_groups_xml(element_root_old)

    # find the used objects in device-group hierarchy
    objs_to_copy = {}
    for dg in reversed_ancestors_list_to_copy:
        print("-----------------------------------------", dg)

        if dg not in objs_to_copy:
            objs_to_copy[dg] = {}

        # the ancestors needed in reverse order to start with the nearest parent dg of current dg
        reversed_dg_ancestors = reversed(dg_data_old[dg]["ancestors"])
        reversed_dg_ancestors_list = list(reversed_dg_ancestors)

        obj_types = ["address", "address-group"]
        for obj_type in obj_types:

            if obj_type not in objs_to_copy[dg]:
                objs_to_copy[dg][obj_type] = []

            if "address" in obj_type:
                rulebase_location = "rulebase-addr"
            elif "service" in obj_type:
                rulebase_location = "rulebase-svc"
            elif "application" in obj_type:
                rulebase_location = "rulebase-app"
            else:
                rulebase_location = "rulebase-god-knows"

            used_obj_list = []
            # check objects from the current dg in rulebase of current dg.
            if len(dg_data_old[dg][obj_type]) > 0:
                for obj_name in dg_data_old[dg][obj_type]:
                    # check group members (if object type is a group, we have to copy the members
                    # from the device-group where it is first defined in the ancestor list of the device-groups).
                    if "group" in obj_type:
                        obj_type_new = obj_type.replace("-group", "")
                        resolved_grp = resolve_group(dg_data_old, dg, obj_name)
                        for sub_obj_name in resolved_grp:
                            # check if member object exists on current dg.
                            if sub_obj_name in dg_data_old[dg][obj_type_new] and sub_obj_name not in used_obj_list:
                                print("group member is in local dg: ", dg)
                                used_obj_list.append(sub_obj_name)
                                objs_to_copy[dg][obj_type_new].append(sub_obj_name)
                            # check if member object exists in ancestor dgs of the current dg.
                            else:
                                for dg_ancestor in reversed_dg_ancestors_list:
                                    if dg_ancestor not in objs_to_copy:
                                        objs_to_copy[dg_ancestor] = {}
                                    if obj_type not in objs_to_copy[dg_ancestor]:
                                        objs_to_copy[dg_ancestor][obj_type] = []
                                    if sub_obj_name in dg_data_old[dg_ancestor][obj_type_new] and sub_obj_name not in used_obj_list:
                                        # address found in ancestor dg.
                                        print("group member is in ancestor dg: ", dg)
                                        used_obj_list.append(sub_obj_name)
                                        objs_to_copy[dg_ancestor][obj_type_new].append(sub_obj_name)

                    # check object from the current dg is used in rulebase of current dg.
                    if obj_name in dg_data_old[dg][rulebase_location]:
                        print("object ", obj_type, "with name ", obj_name, " used from current dg, ", dg)
                        used_obj_list.append(obj_name)
                        objs_to_copy[dg][obj_type].append(obj_name)

            # check object from the ancestor dg is used in rulebase of current dg.
            for dg_ancestor in reversed_dg_ancestors_list:
                if len(dg_data_old[dg_ancestor][obj_type]) > 0:
                    for obj_name_anc in dg_data_old[dg_ancestor][obj_type]:
                        if dg_ancestor not in objs_to_copy:
                            objs_to_copy[dg_ancestor] = {}
                        if obj_type not in objs_to_copy[dg_ancestor]:
                            objs_to_copy[dg_ancestor][obj_type] = []
                        if obj_name_anc in dg_data_old[dg][rulebase_location] and obj_name_anc not in used_obj_list:
                            print("object ", obj_type, "with name ", obj_name_anc, " used from ancestor dg,  ", dg_ancestor)
                            used_obj_list.append(obj_name_anc)
                            objs_to_copy[dg_ancestor][obj_type].append(obj_name_anc)

    # create new xml Element
    dg_xml_to_copy = ET.Element('device-group')
    for dg_to_copy in objs_to_copy:
        # create device-group
        dg_new_entry = ET.SubElement(dg_xml_to_copy, 'entry', name=dg_to_copy)
        for obj_type in objs_to_copy[dg_to_copy]:
            # create xml subelement
            dg_new_subentry = ET.SubElement(dg_new_entry, obj_type)

            for obj_name in objs_to_copy[dg_to_copy][obj_type]:
                # clone the xml element for object only if it does not exist in the new dg
                if dg_to_copy not in dg_data_new or obj_type not in dg_data_new[dg_to_copy] or obj_name not in dg_data_new[dg_to_copy][obj_type]:
                    print("object", obj_name, "not found in destination configuration. I have created the object to the dg ", dg_to_copy)
                    obj_item_xpath = "./" + obj_type + '/entry[@name=' + '\'' + obj_name + '\']'
                    xml_old_item = dgs_xml_dict_old[dg_to_copy].find(obj_item_xpath)
                    dg_new_subentry.append(xml_old_item)
                else:
                    print("object", obj_name, " found in destination configuration.")

    new_tree = ET.ElementTree(dg_xml_to_copy)
    ET.indent(new_tree, space="\t", level=0)
    new_tree.write(result_output, encoding="utf-8")

if __name__ == "__main__":
    main(sys.argv[1:])
