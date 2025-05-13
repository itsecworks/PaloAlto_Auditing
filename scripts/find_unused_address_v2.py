#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the unused addresses within panorama device-group hierarchy.
# It also checks fqdn address type if resolvable
#
import pdb
import sys
import xml.etree.ElementTree as ET
import time
import socket
from threading import Thread


def is_resolve_fqdn(fqdns):

    for fqdn in fqdns:
        try:
            socket.gethostbyname(fqdn)
            result = "{h}: {a}\n".format(h=fqdn, a=True)

        except Exception:
            # fail gracefully!
            result = "{h}: {a}\n".format(h=fqdn, a=False)

        resolvable_ips.append(result)


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

        for item in group_items:
            # First check if it's a direct address in this DG
            if item in dg_data[dg_name].get("address", []):
                result.append(item)
            # Then check if it's another group in this DG
            elif item in dg_data[dg_name].get("address-group", {}):
                helper(dg_name, item)
            else:
                # Not found in current DG, check ancestors
                reversed_ancestors = reversed(dg_data[dg_name]["ancestors"])
                reversed_ancestors_list = list(reversed_ancestors)
                for ancestor in reversed_ancestors_list:
                    if item in dg_data[ancestor].get("address", []):
                        result.append(item)
                        break
                    elif item in dg_data[ancestor].get("address-group", {}):
                        helper(ancestor, item)
                        break

    helper(dg_name, group_name)
    return result


def get_members(xml_element, xpath):

    member_list = set()
    xml_elements = xml_element.findall(xpath)
    if xml_elements is not None:
        for member in xml_elements:
            member_list.add(member.text)
    return member_list


def get_object_names(dg, obj_type):

    if 'group' in obj_type or 'fqdn' in obj_type:
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
                obj_list[obj_name] = get_members(entry, obj_items_xpath)
            elif 'fqdn' in obj_type and entry.find("fqdn") is not None:
                # we need the value for the object name if fqdn to be able to resolve it.
                obj_list[obj_name].add(entry.find("fqdn").text)
            elif 'fqdn' not in obj_type:
                obj_list.add(obj_name)

    return obj_list


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


def main(argv):

    file_path = 'C:/Users/dakos/Downloads/'
    xml_input = file_path + '14185.xml'
    #xml_output = xml_input.replace('.xml', '_mod.xml')
    time_str = time.strftime("%Y%m%d_%H%M%S")
    result_output = file_path + 'paloalto_fqdn_audit_' + time_str + '.csv'

    print("script start timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    tree = ET.parse(xml_input)
    element_root = tree.getroot()
    ro_element = element_root.find("./readonly")
    print("xml loaded timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    dg_data = collect_dg_data(element_root, ro_element)

    print("time after dictionary created : ", time.strftime("%Y%m%d_%H%M%S"))
    f = open(result_output, "x")
    # extracts address-groups used in rules
    # after first usage of an address-group no same name addr-grp can be inserted from any ancestor dg
    for dg in dg_data:
        print("-----------------------------------------", dg)
        used_groups = []
        # check address-groups in rulebase of current dg.
        # If found resolve the group in rulebase to its address elements and remove group name.
        if len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:

                # check address-group in rulebase of current dg.
                if addr_grp in dg_data[dg]["rulebase-addr"]:
                    print("address-group ", addr_grp, " used from current dg, ", dg)
                    used_groups.append(addr_grp)
                    resolved_grp = resolve_group(dg_data, dg, addr_grp)
                    for member in resolved_grp:
                        dg_data[dg]["rulebase-addr"].add(member)
                    dg_data[dg]["rulebase-addr"].remove(addr_grp)

        # check address-groups of ancestor dg in rulebase of current dg.
        # the ancestors needed in reverse order to start wit the nearest parent dg of current dg
        reversed_ancestors = reversed(dg_data[dg]["ancestors"])
        reversed_ancestors_list = list(reversed_ancestors)
        for dg_ancestor in reversed_ancestors_list:
            # check address group in ancestor
            for addr_grp_anc in dg_data[dg_ancestor]["address-group"]:
                if addr_grp_anc in dg_data[dg]["rulebase-addr"] and addr_grp_anc not in used_groups:
                    print("address-group ", addr_grp_anc, " used from ancestor dg,  ", dg_ancestor)
                    used_groups.append(addr_grp_anc)
                    resolved_grp_anc = resolve_group(dg_data, dg_ancestor, addr_grp_anc)
                    for member in resolved_grp_anc:
                        dg_data[dg]["rulebase-addr"].add(member)
                    dg_data[dg]["rulebase-addr"].remove(addr_grp_anc)

    for dg in dg_data:
        print("-----------------------------------------", dg)
        for fqdn in dg_data[dg]["fqdn"]:
            if fqdn not in dg_data[dg]["rulebase-addr"]:
                used_fqdn = False
                for dg_descendant in dg_data[dg]["descendants"]:
                    if used_fqdn is False and fqdn in dg_data[dg_descendant]["rulebase-addr"]:
                        used_fqdn = True
                    elif used_fqdn is True and fqdn in dg_data[dg_descendant]["rulebase-addr"]:
                        print("duplicated fqdn ", fqdn, " from dg ", dg_descendant, " with dg ", dg)
                        f.write("duplicated fqdn " + fqdn + " from dg " + dg_descendant + " with dg " + dg + "\n")
                if used_fqdn is False:
                    print("not used fqdn ", fqdn, " from dg ", dg)
                    f.write("not used fqdn " + fqdn + " from dg " + dg + "\n")

        # here we resolve the fqdns to ip if exists. it is multithreaded.
        threads = list()

        chunk_size = 3
        for i in range(0, len(dg_data[dg]["fqdn"]), chunk_size):
            fqdns_chunk = dg_data[dg]["fqdn"][i:i + chunk_size]
            x = Thread(target=is_resolve_fqdn, args=(fqdns_chunk,))
            threads.append(x)
            x.start()

        for fqdns_chunk, thread in enumerate(threads):
            thread.join()
        print(resolvable_ips)


if __name__ == "__main__":
    global resolvable_ips
    resolvable_ips = []
    main(sys.argv[1:])
