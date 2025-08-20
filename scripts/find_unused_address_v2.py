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
            socket.gethostbyname(fqdn[1])
            result = [fqdn[0], True]

        except Exception:
            # fail gracefully!
            result = [fqdn[0], False]

        resolvable_ips.append(result)


# Function to find all ancestors (parents, grandparents, great-grandparents...) for a device-group recursively
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


# Function to find all descendants (children, grandchildren, and great-grandchildren...) for a device-group recursively
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
    dg_children = {'shared': []}
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


def resolve_group_to_gr_only(dg_data, dg_name, group_name, visited=None):

    # this function collects groups with group members only.
    # The result is a list of group names in groups for a given group and device-group.
    if visited is None:
        visited = set()
    result_grps = []

    def helper(dg_name, group_name):
        if (dg_name, group_name) in visited:
            print("loop in device-groups address-group detected!")
            return
        visited.add((dg_name, group_name))

        # safely accessing nested dictionaries with get method. Get method returns None if key does not exist
        # in get method we set the default values as well
        group_members = dg_data.get(dg_name, {}).get("address-group", {}).get(group_name, [])

        for gr_member in group_members:
            # check if it's another group in this DG
            if gr_member in dg_data[dg_name].get("address-group", {}):
                result_grps.append(gr_member)
                helper(dg_name, gr_member)
            else:
                # Not found in current DG, check ancestors
                reversed_ancestors = reversed(dg_data[dg_name]["ancestors"])
                reversed_ancestors_list = list(reversed_ancestors)
                for ancestor in reversed_ancestors_list:
                    if gr_member in dg_data[ancestor].get("address-group", {}):
                        result_grps.append(gr_member)
                        helper(ancestor, gr_member)
                        break

    helper(dg_name, group_name)
    return result_grps


def resolve_group_to_addr_only(dg_data, dg_name, group_name, visited=None):

    # this function resolves group members if they are groups, as a result you get group members with addresses only.
    if visited is None:
        visited = set()
    result = []
    result_grps = []

    def helper(dg_name, group_name):
        if (dg_name, group_name) in visited:
            print("loop in device-groups address-group detected!")
            return
        visited.add((dg_name, group_name))

        # safely accessing nested dictionaries with get method
        group_members = dg_data.get(dg_name, {}).get("address-group", {}).get(group_name, [])

        for gr_member in group_members:
            # First check if it's a direct address in this DG
            if gr_member in dg_data[dg_name].get("address", []):
                result.append(gr_member)
            # Then check if it's another group in this DG
            elif gr_member in dg_data[dg_name].get("address-group", {}):
                result_grps.append(gr_member)
                helper(dg_name, gr_member)
            else:
                # Not found in current DG, check ancestors
                reversed_ancestors = reversed(dg_data[dg_name]["ancestors"])
                reversed_ancestors_list = list(reversed_ancestors)
                for ancestor in reversed_ancestors_list:
                    if gr_member in dg_data[ancestor].get("address", []):
                        result.append(gr_member)
                        break
                    elif gr_member in dg_data[ancestor].get("address-group", {}):
                        helper(ancestor, gr_member)
                        break

    helper(dg_name, group_name)
    return result


def get_members(xml_element, xpath):

    member_list = set()
    xml_elements = xml_element.findall(xpath)
    if xml_elements is not None:
        member_list = set(member.text for member in xml_elements)
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
                obj_list[obj_name] = {}
                obj_list[obj_name] = entry.find("fqdn").text
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


def find_used_ags(dg_data):

    used_groups = {}
    for dg in dg_data:
        used_groups[dg] = []
        if len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:
                if addr_grp in dg_data[dg]["rulebase-addr"]:
                    groups_in_group = resolve_group_to_gr_only(dg_data, dg, addr_grp)
                    used_groups[dg].append(addr_grp)
                    used_groups[dg].extend(groups_in_group)
                for child_dg in dg_data[dg]["descendants"]:
                    if addr_grp in dg_data[child_dg]["rulebase-addr"]:
                        groups_in_group = resolve_group_to_gr_only(dg_data, dg, addr_grp)
                        used_groups[dg].append(addr_grp)
                        used_groups[dg].extend(groups_in_group)

    return used_groups


def find_unused_ags(dg_data):

    cli_cmds_str = ''
    for dg in dg_data:
        if len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:
                if addr_grp not in dg_data[dg]["rulebase-addr"]:
                    unused_ag = True
                    for child_dg in dg_data[dg]["descendants"]:
                        if addr_grp in dg_data[child_dg]["rulebase-addr"]:
                            unused_ag = False
                    if unused_ag:
                        cli_cmds_str += "not_used_address-group: delete device-group \"" + dg + "\" address-group \"" + addr_grp + "\"\n"

    return cli_cmds_str


def find_unused_ags_v2(dg_data):

    used_agroups = find_used_ags(dg_data)
    cli_cmds_str = ''
    for dg in dg_data:
        if len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:
                if addr_grp not in used_agroups[dg]:
                    unused_ag = True
                    for child_dg in dg_data[dg]["descendants"]:
                        if addr_grp in used_agroups[child_dg]:
                            unused_ag = False
                    if unused_ag:
                        cli_cmds_str += "not_used_address-group: delete device-group \"" + dg + "\" address-group \"" + addr_grp + "\"\n"

    return cli_cmds_str



def extract_address_group_in_rules(dg_data):

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
                    print("address-group ", addr_grp, " used_from_current_dg, ", dg)
                    used_groups.append(addr_grp)
                    resolved_grp = resolve_group_to_addr_only(dg_data, dg, addr_grp)
                    for member in resolved_grp:
                        dg_data[dg]["rulebase-addr"].add(member)
                    dg_data[dg]["rulebase-addr"].remove(addr_grp)

        # check address-groups of ancestor dg in rulebase of current dg.
        # the ancestors needed in reverse order to start wit the nearest parent dg of current dg
        reversed_ancestors = reversed(dg_data[dg]["ancestors"])
        reversed_ancestors_list = list(reversed_ancestors)
        for dg_ancestor in reversed_ancestors_list:
            # iterate over the address groups in ancestor dg
            for addr_grp_anc in dg_data[dg_ancestor]["address-group"]:
                if addr_grp_anc in dg_data[dg]["rulebase-addr"] and addr_grp_anc not in used_groups:
                    print("address-group ", addr_grp_anc, " used_from_ancestor_dg,  ", dg_ancestor)
                    used_groups.append(addr_grp_anc)
                    resolved_grp_anc = resolve_group_to_addr_only(dg_data, dg_ancestor, addr_grp_anc)
                    for member in resolved_grp_anc:
                        dg_data[dg]["rulebase-addr"].add(member)
                    dg_data[dg]["rulebase-addr"].remove(addr_grp_anc)
                elif addr_grp_anc in dg_data[dg]["rulebase-addr"] and addr_grp_anc in used_groups:
                    print("hoppa parent dg has same address-group. parent-dg ", dg_ancestor, " address-group ", addr_grp_anc," with child dg ", dg)

    return dg_data

def main(argv):

    file_path = 'C:/Users/dakos/Downloads/'
    xml_input = file_path + '16305.xml'
    #xml_output = xml_input.replace('.xml', '_mod.xml')
    time_str = time.strftime("%Y%m%d_%H%M%S")

    unused_addresses_file = file_path + 'paloalto_unused_addresses_' + time_str + '.txt'
    not_resolvable_fqdns_file = file_path + 'paloalto_notresolvable_fqdns_' + time_str + '.txt'
    multiplied_addresses_file = file_path + 'paloalto_multiplied_addresses_' + time_str + '.txt'
    unused_address_groups_file = file_path + 'paloalto_unused_address_groups_' + time_str + '.txt'

    # prepare the output file
    f_unused_addrs = open(unused_addresses_file, "x")
    f_unres_fqdns = open(not_resolvable_fqdns_file, "x")
    f_multiplied_addrs = open(multiplied_addresses_file, "x")
    f_unused_ags = open(unused_address_groups_file, "x")


    print("script start timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    tree = ET.parse(xml_input)
    element_root = tree.getroot()
    ro_element = element_root.find("./readonly")
    print("xml loaded timestamp : ", time.strftime("%Y%m%d_%H%M%S"))

    dg_data = collect_dg_data(element_root, ro_element)

    print("time after dictionary created : ", time.strftime("%Y%m%d_%H%M%S"))

    # find unused groups
    cli_commands = find_unused_ags_v2(dg_data)
    f_unused_ags.write(cli_commands)

    # extracts address-groups used in rules
    dg_data_extracted = extract_address_group_in_rules(dg_data)

    # find multiplied fqdns and not used fqdns
    addr_type = "fqdn"
    for dg in dg_data_extracted:
        print("-----------------------------------------", dg)
        dg_quoted = "\"" + dg + "\""
        dup_count = 0
        not_used_count = 0
        not_resolved_count = 0
        for address_object in dg_data_extracted[dg][addr_type]:
            address_object_quoted = "\"" + address_object + "\""
            if address_object not in dg_data_extracted[dg]["rulebase-addr"]:
                used_address = False
            else:
                used_address = True
            for dg_descendant in dg_data_extracted[dg]["descendants"]:
                if used_address is False and address_object in dg_data_extracted[dg_descendant]["rulebase-addr"]:
                    used_address = True
                if address_object in dg_data_extracted[dg_descendant][addr_type]:
                    dup_count += 1
                    dg_descendant_quoted = "\"" + dg_descendant + "\""
                    #print("duplicated_fqdn_name ", fqdn_quoted, " from_dg ", dg_quoted, " in ", dg_descendant_quoted)
                    f_multiplied_addrs.write("duplicated_fqdn_name " + address_object_quoted + " from_dg " + dg_quoted + " in " + dg_descendant_quoted + "\n")
            if used_address is False:
                not_used_count += 1
                #print("not_used_fqdn ", fqdn_quoted, " from dg ", dg_quoted)
                f_unused_addrs.write("not_used_fqdn: delete device-group " + dg_quoted + " address " + address_object_quoted + "\n")

        # here we resolve the fqdns to ip if exists. it is multithreaded.
        threads = list()

        # since I cannot iterate over a dict with range and len as used for chunks :-)
        # I convert the dict to list first
        global resolvable_ips
        resolvable_ips = []
        fqdn_list = []
        for fqdn_obj_name in dg_data[dg]["fqdn"]:
            domain_name = dg_data[dg]["fqdn"][fqdn_obj_name]
            fqdn_item = [fqdn_obj_name, domain_name]
            fqdn_list.append(fqdn_item)
        # split up the list for multithreaded dns resolution check.
        chunk_size = 3
        for i in range(0, len(fqdn_list), chunk_size):
            fqdns_chunk = fqdn_list[i:i + chunk_size]
            x = Thread(target=is_resolve_fqdn, args=(fqdns_chunk,))
            threads.append(x)
            x.start()

        for fqdns_chunk, thread in enumerate(threads):
            thread.join()

        for fqdn_list in resolvable_ips:
            if not fqdn_list[1]:
                not_resolved_count += 1
                fqdn1_quoted = "\"" + fqdn_list[0] + "\""
                #print("not_resolvable_fqdn ", fqdn1_quoted, " from_dg ", dg_quoted)
                f_unres_fqdns.write("not_resolvable_fqdn: delete device-group " + dg_quoted + " address " + fqdn1_quoted + "\n")

        print("sum for device-group:", dg_quoted, ":", "duplicated: ", dup_count, "not_used:", not_used_count, "unresolved:", not_resolved_count)

if __name__ == "__main__":
    main(sys.argv[1:])
