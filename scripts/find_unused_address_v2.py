#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the unused addresses within panorama device-group hierarchy.
# It also checks fqdn address type if resolvable
#

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


def main(argv):

    file_path = 'C:/Users/dakos/Downloads/'
    xml_input = file_path + '14185.xml'
    xml_output = xml_input.replace('.xml', '_mod.xml')
    time_str = time.strftime("%Y%m%d_%H%M%S")
    result_output = file_path + 'paloalto_address_audit_' + time_str + '.csv'

    print("script start timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    tree = ET.parse(xml_input)
    root = tree.getroot()
    ro_element = root.find("./readonly")
    print("xml loaded timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    dg_children = find_children(ro_element)
    dg_data = {}

    pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
    for key in pa_all_dgs:
        xpath = pa_all_dgs[key]
        for dg in root.findall(xpath):
            if key == "default":
                dg_name = dg.attrib["name"]
            else:
                dg_name = key
            print("loading up to dg_data for ", dg_name)
            dg_data[dg_name] = {}
            dg_data[dg_name]["descendants"] = find_descendants(dg_children, dg_name)
            dg_data[dg_name]["ancestors"] = find_ancestors(ro_element, dg_name)
            dg_data[dg_name]["address"] = set()
            dg_data[dg_name]["fqdn"] = set()
            dg_data[dg_name]["address-group"] = {}

            dg_address_list = dg.findall("./address/entry")
            dg_addr_grp_list = dg.findall("./address-group/entry")
            if dg_address_list is not None:
                for entry in dg_address_list:
                    address_name = entry.get("name")
                    if entry.find("fqdn") is not None:
                        dg_data[dg_name]["fqdn"].add(address_name)
                    dg_data[dg_name]["address"].add(address_name)
            if dg_addr_grp_list is not None:
                for entry in dg_addr_grp_list:
                    addr_group_name = entry.get("name")
                    dg_data[dg_name]["address-group"][addr_group_name] = []
                    members = entry.findall("./static/member")
                    if members is not None:
                        for member in members:
                            dg_data[dg_name]["address-group"][addr_group_name].append(member.text)

            rule_positions = ["pre-rulebase", "post-rulebase"]
            dg_data[dg_name]["rulebase"] = set()
            for rule_position in rule_positions:
                dg_data[dg_name][rule_position] = {}
                rb_xpath = "./" + rule_position
                rulebase_xml = dg.find(rb_xpath)
                if rulebase_xml is not None:
                    for rule_type_xml in rulebase_xml:
                        address_locations = ["source", "destination"]
                        for addr_location in address_locations:
                            rules_xml = rule_type_xml.findall('./rules/entry')
                            if rules_xml is not None:
                                for rule in rules_xml:
                                    rule_addr_xpath = './' + addr_location + '/member'
                                    rule_addresses_xml = rule.findall(rule_addr_xpath)
                                    if rule_addresses_xml is not None:
                                        for member in rule_addresses_xml:
                                            dg_data[dg_name]["rulebase"].add(member.text)

    print("time after dictionary created : ", time.strftime("%Y%m%d_%H%M%S"))
    f = open("myfile.txt", "x")
    # extracts address-groups used in rules
    # after first usage of an address-group no same name addr-grp can be inserted from any ancestor dg
    for dg in dg_data:
        print("-----------------------------------------", dg)
        used_groups = []
        # check address in address-groups
        if len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:
                #print(resolved_grp)
                # check address-group in rulebase
                if addr_grp in dg_data[dg]["rulebase"]:
                    print("address-group ", addr_grp, " used from current dg, ", dg)
                    used_groups.append(addr_grp)
                    resolved_grp = resolve_group(dg_data, dg, addr_grp)
                    #for member in dg_data[dg]["address-group"][addr_grp]:
                    for member in resolved_grp:
                        dg_data[dg]["rulebase"].add(member)
                    dg_data[dg]["rulebase"].remove(addr_grp)
        # the ancestors needed in reverse order
        reversed_ancestors = reversed(dg_data[dg]["ancestors"])
        reversed_ancestors_list = list(reversed_ancestors)
        for dg_ancestor in reversed_ancestors_list:
            # check address group in ancestor
            for addr_grp_anc in dg_data[dg_ancestor]["address-group"]:
                if addr_grp_anc in dg_data[dg]["rulebase"] and addr_grp_anc not in used_groups:
                    print("address-group ", addr_grp_anc, " used from ancestor dg,  ", dg)
                    used_groups.append(addr_grp_anc)
                    resolved_grp_anc = resolve_group(dg_data, dg_ancestor, addr_grp_anc)
                    for member in resolved_grp_anc:
                        dg_data[dg]["rulebase"].add(member)
                    dg_data[dg]["rulebase"].remove(addr_grp_anc)

    for dg in dg_data:
        print("-----------------------------------------", dg)
        for fqdn in dg_data[dg]["fqdn"]:
            if fqdn not in dg_data[dg]["rulebase"]:
                used_fqdn = False
                for dg_descendant in dg_data[dg]["descendants"]:
                    if used_fqdn is False and fqdn in dg_data[dg_descendant]["rulebase"]:
                        used_fqdn = True
                if used_fqdn is False:
                    print("not used fqdn ", fqdn, " from dg ", dg)
                    f.write("not used fqdn " + fqdn + " from dg " + dg + "\n")

if __name__ == "__main__":
    main(sys.argv[1:])
