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


def is_resolve_fqdn(fqdns: list):
    """

    :param fqdns: list with 2 items: 0-fqdn object name and 1-fqdn value
    :return: extends the global variable, resolvable_ips with object name and true if fqdn is resolvable or false if not
    :rtype: list
    """
    for fqdn in fqdns:
        try:
            socket.gethostbyname(fqdn[1])
            result = [fqdn[0], True]

        except Exception:
            # fail gracefully!
            result = [fqdn[0], False]

        resolvable_ips.append(result)


def find_ancestors(ro_element: ET.Element, child_dg_name: str) -> list:
    """

    :param ro_element: readonly xml element from panorama config
    :param child_dg_name: name of the child device-group to find all parents and grandparents
    :return: return all ancestors (parents, grandparents, great-grandparents...) for a device-group recursively
    :rtype: list
    """
    if "shared" in child_dg_name:
        return []

    dg = ro_element.find("./devices/entry/device-group/entry[@name='" + child_dg_name + "']")
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


def find_descendants(dg_children: dict, parent_dg_name: str) -> list:
    """

    :param dg_children: a dictionary with key as the device-group and with value as a list of direct child device-groups.
    :param parent_dg_name: device-group name for that function finds the children, grandchildren, etc.
    :return: all descendants (children, grandchildren, and great-grandchildren...) for a parent device-group recursively.
    :rtype: list
    """
    dg_descendants = []  # List to store descendants of a device-group
    # Find all children of the given parent
    if parent_dg_name in dg_children:
        children = dg_children[parent_dg_name]

        for child in children:
            # add a single list element to the descendant list
            dg_descendants.append(child)
            # extend with multiple list elements the device-group with recursively get descendants
            dg_descendants.extend(find_descendants(dg_children, child))

    return dg_descendants


def find_children(ro_element: ET.Element) -> dict:
    """

    :param ro_element: readonly xml element from panorama configuration
    :return: a dictionary with key as the device-group and with value as a list of direct child device-groups.
    :rtype: dict
    """
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


def resolve_group_to_gr_only(dg_data: dict, dg_name: str, group_name: str, visited: set = None) -> list:
    """

    :param dg_data: dictionary that contains for each device-group the ancestors, descendants and objects
    :param dg_name: name of the device-group in that the address-group exists
    :param group_name: name of the address-group objects
    :param visited: a list of address-groups that have been visited already, it is used to avoid loops
    :return: list of groups names only if group contained group for a given group and device-group
    :rtype: list
    """
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


def resolve_group_to_addr_only(dg_data: dict, dg_name: str, group_name: str, visited: set = None) -> list:
    """

    :param dg_data: dictionary that contains for each device-group the ancestors, descendants and objects
    :param dg_name: name of the device-group in that the address-group exists
    :param group_name: name of the address-group objects
    :param visited: a list of address-groups that have been visited already, it is used to avoid loops
    :return: resolves group members if they are groups, as a result you get group members with address names only.
    :rtype: list
    """
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


def get_members(xml_element: ET.Element, xpath: str) -> set:
    """

    :param xml_element: is an xml element that has multiple child elements
    :param xpath: is the xpath to find within the xml element the child elements
    :return: list of members xml text (not the tag), the output is set so duplicated names will be removed.
    :rtype: set
    """
    member_list = set()
    xml_elements = xml_element.findall(xpath)
    if xml_elements is not None:
        member_list = set(member.text for member in xml_elements)
    return member_list


def get_object_values(dg: ET.Element) -> dict:
    """

    :param dg:
    :return:
    """
    obj_list = {"address_values": {}, "fqdn_values": {}}
    obj_xpath = './address/entry'
    objects_xml = dg.findall(obj_xpath)
    if "name" in dg.attrib:
        dg_name = dg.get("name")
    else:
        dg_name = "shared"
    if objects_xml is not None:
        for entry in objects_xml:
            obj_name = entry.get("name")
            obj_value_xml = entry.find("fqdn")
            if obj_value_xml is not None:
                obj_list["fqdn_values"][obj_value_xml.text] = {}
                obj_list["fqdn_values"][obj_value_xml.text][dg_name] = obj_name
            else:
                obj_value_xml = entry.find("ip-netmask")
                if obj_value_xml is None:
                    obj_value_xml = entry.find("ip-range")
                if obj_value_xml is None:
                    print("address value not clear...")

                obj_list["address_values"][obj_value_xml.text] = {}
                obj_list["address_values"][obj_value_xml.text][dg_name] = obj_name

    return obj_list


def get_object_data(dg: ET.Element, obj_type: str) -> dict:
    """

    :param dg: xml element of a device-group
    :param obj_type: type of the object like address, address-group, fqdn address
    :return: the list of objects in dictionary. if it is a group it adds the members name as a value.
             If it is fqdn it adds the value of an address object as a value and the key is the object name
    :rtype: dict
    """
    sum_name = obj_type + "_sum"
    if 'fqdn' in obj_type:
        obj_list = {}
    elif 'group' in obj_type:
        obj_list = {sum_name: set()}
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
                # sum_name for groups contains all members of all groups in one single list (set)
                obj_list[sum_name].update(obj_list[obj_name])
            elif 'fqdn' in obj_type and entry.find("fqdn") is not None:
                # we need the value for the object name if fqdn to be able to resolve it.
                obj_list[obj_name] = {}
                obj_list[obj_name] = entry.find("fqdn").text
            elif 'fqdn' not in obj_type:
                obj_list.add(obj_name)

    return obj_list


def get_rule_object_names(dg: ET.Element) -> dict:
    """

    :param dg: xml element of a device-group
    :return: a dictionary with every type of rules and per rule the src + dst, svc, app in set (no duplicates)
            the pre or post rulebase positions are removed here. rule position and rule type is not needed.
    :rtype: dict
    """
    rule_objects = {}
    rule_positions = ["pre-rulebase", "post-rulebase"]
    rule_objects["rulebase-addr"] = set()
    rule_objects["rulebase-svc"] = set()
    rule_objects["rulebase-app"] = set()

    for rule_position in rule_positions:
        rb_xpath = "./" + rule_position
        rulebase_xml = dg.find(rb_xpath)
        rule_objects[rule_position] = {}
        if rulebase_xml is not None:
            for rule_type_xml in rulebase_xml:
                rules_xml = rule_type_xml.findall('./rules/entry')
                if rules_xml is not None and len(rules_xml) > 0:
                    rule_objects[rule_position][rule_type_xml.tag] = {}
                    rule_objects[rule_position][rule_type_xml.tag]["rules"] = {}
                    rule_objects[rule_position][rule_type_xml.tag]["source"] = set()
                    rule_objects[rule_position][rule_type_xml.tag]["destination"] = set()
                    for rule in rules_xml:
                        # rulebase address objects
                        rule_name = rule.attrib["name"]
                        rule_objects[rule_position][rule_type_xml.tag]["rules"][rule_name] = {}
                        address_locations = ["source", "destination"]
                        for addr_location in address_locations:
                            rule_addr_xpath = './' + addr_location + '/member'
                            members = get_members(rule, rule_addr_xpath)
                            rule_objects["rulebase-addr"].update(members)
                            rule_objects[rule_position][rule_type_xml.tag][addr_location].update(members)
                            rule_objects[rule_position][rule_type_xml.tag]["rules"][rule_name][addr_location] = set()
                            rule_objects[rule_position][rule_type_xml.tag]["rules"][rule_name][addr_location].update(members)

                        # rulebase services
                        rule_svc_xpath = './service/member'
                        rule_objects["rulebase-svc"].update(get_members(rule, rule_svc_xpath))
                        # rulebase applications
                        rule_app_xpath = './application/member'
                        rule_objects["rulebase-app"].update(get_members(rule, rule_app_xpath))

    return rule_objects


def collect_obj_values (xml_root: ET.Element, ro_element: ET.Element) -> dict:

    dg_children = find_children(ro_element)
    dg_objects = {"fqdn_values": {}, "address_values": {}}

    pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
    for key in pa_all_dgs:
        xpath = pa_all_dgs[key]
        for dg in xml_root.findall(xpath):
            if key == "default":
                dg_name = dg.attrib["name"]
            else:
                dg_name = key
            print("loading up to dg_data for ", dg_name)
            # sort address objects based on values
            values_dict = get_object_values(dg)
            for obj_typeval_name in values_dict:
                for value_key in values_dict[obj_typeval_name]:
                    if value_key not in dg_objects[obj_typeval_name]:
                        dg_objects[obj_typeval_name][value_key] = values_dict[obj_typeval_name][value_key]
                    else:
                        dg_objects[obj_typeval_name][value_key].update(values_dict[obj_typeval_name][value_key])

    return dg_objects


def collect_dg_data(xml_root: ET.Element, ro_element: ET.Element) -> dict:
    """

    :param xml_root: the complete xml config of palo alto panorama
    :param ro_element: readonly xml element from panorama configuration
    :return: it collects from the panorama xml per device-group the
             - ancestors
             - descendants
             - different objects types: "fqdn", "address", "address-group", "service", "service-group", "application-group",
                         "application"
             - rules src, dst in one field and service and applications
    :rtype: dict
    """
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
            obj_types = ["fqdn", "address", "address-group", "service", "service-group", "application-group",
                         "application"]

            for obj_type in obj_types:
                dg_objects[dg_name][obj_type] = get_object_data(dg, obj_type)

            rule_objects = get_rule_object_names(dg)
            dg_objects[dg_name].update(rule_objects)

    return dg_objects


def find_used_ags(dg_data: dict) -> dict:
    """

    :param dg_data: different objects from each device-groups like addresses, ancestors, etc
    :return: dictionary of used groups per device-group checking the device-group hierarchy.
    """
    used_groups = {}
    for dg in dg_data:
        used_groups[dg] = []
        if "address-group" in dg_data[dg] and len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:
                if addr_grp in dg_data[dg]["rulebase-addr"]:
                    used_groups[dg].append(addr_grp)
                    groups_in_group = resolve_group_to_gr_only(dg_data, dg, addr_grp)
                    used_groups[dg].extend(groups_in_group)
                for dg_descendant in dg_data[dg]["descendants"]:
                    if addr_grp in dg_data[dg_descendant]["rulebase-addr"]:
                        used_groups[dg].append(addr_grp)
                        groups_in_group = resolve_group_to_gr_only(dg_data, dg, addr_grp)
                        used_groups[dg].extend(groups_in_group)

    return used_groups


def find_unused_ags_v2(dg_data: dict) -> str:
    """

    :param dg_data: different objects from each device-groups like addresses, ancestors, etc.
    :return: a string with the palo alto cli address-group removal configuration.
    """
    used_address_groups = find_used_ags(dg_data)
    cli_cmds_str = ''
    for dg in dg_data:
        if "address-group" in dg_data[dg] and len(dg_data[dg]["address-group"]) > 0:
            for addr_grp in dg_data[dg]["address-group"]:
                if addr_grp not in used_address_groups[dg]:
                    unused_ag = True
                    for dg_descendant in dg_data[dg]["descendants"]:
                        if addr_grp in used_address_groups[dg_descendant]:
                            unused_ag = False
                    if unused_ag:
                        cli_cmds_str += "not_used_address-group: delete device-group \"" + dg + "\" address-group \"" + addr_grp + "\"\n"

    return cli_cmds_str


def extract_address_group_in_rules(dg_data: dict) -> dict:
    """

    :param dg_data: a dictionary with different objects from each device-groups like addresses, ancestors, etc.
    :return: resolves the address-groups in rules to its members. group in groups as well.
    """
    # extracts address-groups used in rules
    # after first usage of an address-group no same name addr-grp can be inserted from any ancestor dg
    for dg in dg_data:
        if "address-group" in dg_data[dg]:
            print("-----------------------------------------", dg)
            used_groups = []
            # check address-groups in rulebase of current dg.
            # If found resolve the group in rulebase to its address elements and remove group name.
            if "rulebase-addr_flat" not in dg_data[dg]:
                dg_data[dg]["rulebase-addr_flat"] = set(dg_data[dg]["rulebase-addr"])
            if len(dg_data[dg]["address-group"]) > 0:
                for addr_grp in dg_data[dg]["address-group"]:
                    # check address-group in rulebase of current dg.
                    if addr_grp in dg_data[dg]["rulebase-addr_flat"]:
                        print("address-group ", addr_grp, " used_from_current_dg, ", dg)
                        used_groups.append(addr_grp)
                        resolved_grp = resolve_group_to_addr_only(dg_data, dg, addr_grp)
                        for member in resolved_grp:
                            dg_data[dg]["rulebase-addr_flat"].add(member)
                        dg_data[dg]["rulebase-addr_flat"].remove(addr_grp)

            # check address-groups of ancestor dg in rulebase of current dg.
            # the ancestors needed in reverse order to start wit the nearest parent dg of current dg.
            reversed_ancestors = reversed(dg_data[dg]["ancestors"])
            reversed_ancestors_list = list(reversed_ancestors)
            for dg_ancestor in reversed_ancestors_list:
                # iterate over the address groups in ancestor dg
                if "rulebase-addr_flat" not in dg_data[dg_ancestor]:
                    dg_data[dg_ancestor]["rulebase-addr_flat"] = set(dg_data[dg_ancestor]["rulebase-addr"])
                for addr_grp_anc in dg_data[dg_ancestor]["address-group"]:
                    if addr_grp_anc in dg_data[dg]["rulebase-addr_flat"] and addr_grp_anc not in used_groups:
                        print("address-group ", addr_grp_anc, " used_from_ancestor_dg,  ", dg_ancestor)
                        used_groups.append(addr_grp_anc)
                        resolved_grp_anc = resolve_group_to_addr_only(dg_data, dg_ancestor, addr_grp_anc)
                        for member in resolved_grp_anc:
                            dg_data[dg]["rulebase-addr_flat"].add(member)
                        dg_data[dg]["rulebase-addr_flat"].remove(addr_grp_anc)
                    elif addr_grp_anc in dg_data[dg]["rulebase-addr_flat"] and addr_grp_anc in used_groups:
                        print("oops, parent dg has same address-group. parent-dg ", dg_ancestor, " address-group ",
                              addr_grp_anc, " with child dg ", dg)

    return dg_data


def find_reference_for_object(dg_data: dict, dg_name: str, obj_name: str, obj_type: str, file) -> bool:
    """

    :param dg_data:
    :param dg_name:
    :param obj_name:
    :param obj_type:
    :param file:
    :return:
    """

    used_object = False
    dg_quoted = "\"" + dg_name + "\""
    obj_name_quoted = "\"" + obj_name + "\""
    if "fqdn" in obj_type:
        obj_group_name = "address-group"
    elif "group" in obj_type:
        obj_group_name = obj_type
    else:
        obj_group_name = obj_type + "-group"
    sum_name = obj_group_name + "_sum"
    if obj_name in dg_data[dg_name][obj_group_name][sum_name]:
        # object is in a group of current dg
        used_object = True
        for group_name in list(dg_data[dg_name][obj_group_name]):
            # address-groups and sum name are on the same level :-) need to exclude from group_name below...
            if obj_name in dg_data[dg_name][obj_group_name][group_name] and group_name not in sum_name:
                # object is here in that group with name group_name
                if len(dg_data[dg_name][obj_group_name][group_name]) == 1:
                    # last item in group, group must be removed
                    find_reference_for_object(dg_data, dg_name, group_name, obj_type, file)
                    del dg_data[dg_name][obj_group_name][group_name]
                else:
                    dg_data[dg_name][obj_group_name][group_name].remove(obj_name)
                    if dg_name == "shared":
                        file.write("reference removal for " + obj_name + " - " + dg_name + " : delete shared address-group " + group_name + " static " + obj_name_quoted + "\n")
                    else:
                        file.write("reference removal for " + obj_name + " - " + dg_name + " : delete device-group " + dg_quoted + " address-group " + group_name + " static " + obj_name_quoted + "\n")

    if obj_name in dg_data[dg_name]["rulebase-addr"]:
        # object is in a rule of current dg
        used_object = True
        rule_positions = ["pre-rulebase", "post-rulebase"]
        for rule_position in rule_positions:
            if rule_position in dg_data[dg_name]:
                for rule_type in dg_data[dg_name][rule_position]:
                    address_locations = ["source", "destination"]
                    for addr_location in address_locations:
                        if obj_name in dg_data[dg_name][rule_position][rule_type][addr_location]:
                            for rule in list(dg_data[dg_name][rule_position][rule_type]["rules"]):
                                if obj_name in dg_data[dg_name][rule_position][rule_type]["rules"][rule][addr_location]:
                                    # rule found
                                    rule_quoted = "\"" + rule + "\""
                                    if len(dg_data[dg_name][rule_position][rule_type]["rules"][rule][addr_location]) == 1:
                                        # last item in rule, rule must be removed.
                                        del dg_data[dg_name][rule_position][rule_type]["rules"][rule]
                                        if dg_name == "shared":
                                            file.write(
                                                "reference removal for " + obj_name + " - " + dg_name + " : delete shared " + rule_position + " " + rule_type + " rules " + rule_quoted + "\n")
                                        else:
                                            file.write(
                                                "reference removal for " + obj_name + " - " + dg_name + " : delete device-group " + dg_quoted + " " + rule_position + " " + rule_type + " rules " + rule_quoted + "\n")

                                    else:
                                        # delete rule src or dst...
                                        dg_data[dg_name][rule_position][rule_type]["rules"][rule][addr_location].remove(obj_name)
                                        if dg_name == "shared":
                                            file.write(
                                                "reference removal for " + obj_name + " - " + dg_name + " : delete shared " + rule_position + " " + rule_type + " rules " + rule_quoted + " " + addr_location + " " + obj_name + "\n")
                                        else:
                                            file.write(
                                                "reference removal for " + obj_name + " - " + dg_name + " : delete device-group " + dg_quoted + " " + rule_position + " " + rule_type + " rules " + rule_quoted + " " + addr_location + " " + obj_name + "\n")
    # check rules from descendants
    for dg_descendant in dg_data[dg_name]["descendants"]:
        dg_descendant_quoted = "\"" + dg_descendant + "\""
        obj_value_diff = False
        if obj_name in dg_data[dg_descendant][obj_type]:
            if dg_data[dg_name][obj_type][obj_name] != dg_data[dg_descendant][obj_type][obj_name]:
                print("object exists in descendant dg and has different value: ", dg_name, dg_descendant, obj_name)
                obj_value_diff = True
            else:
                print("object exists in descendant dg but has same value.")

        if obj_name not in dg_data[dg_descendant][obj_type] or not obj_value_diff:
            if obj_name in dg_data[dg_descendant][obj_group_name][sum_name]:
                # object is in a group of current dg
                used_object = True
                for group_name in list(dg_data[dg_descendant][obj_group_name]):
                    if obj_name == dg_data[dg_descendant][obj_group_name][group_name]:
                        # object is here in that group with name group_name
                        if len(dg_data[dg_descendant][obj_group_name][group_name]) == 1:
                            # last item in group, group must be removed
                            print("last item in group, group must be removed: ", dg_descendant, group_name)
                            find_reference_for_object(dg_data, dg_descendant, group_name, obj_type, file)
                            del dg_data[dg_descendant][obj_group_name][group_name]
                        else:
                            dg_data[dg_descendant][obj_group_name][group_name].remove(obj_name)
                            if dg_descendant == "shared":
                                print("whaaaat? shared as descendant?")
                                file.write(
                                    "reference_removal for " + obj_name + " - " + dg_name + " : delete shared address-group " + group_name + " static " + obj_name + "\n")
                            else:
                                file.write(
                                    "reference_removal for " + obj_name + " - " + dg_name + " : delete device-group" + dg_descendant_quoted + " address-group " + group_name + " static " + obj_name + "\n")

            if obj_name in dg_data[dg_descendant]["rulebase-addr"]:
                # object is in a rule of current dg
                used_object = True
                rule_positions = ["pre-rulebase", "post-rulebase"]
                for rule_position in rule_positions:
                    if rule_position in dg_data[dg_descendant]:
                        for rule_type in dg_data[dg_descendant][rule_position]:
                            address_locations = ["source", "destination"]
                            for addr_location in address_locations:
                                if obj_name in dg_data[dg_descendant][rule_position][rule_type][addr_location]:
                                    for rule in list(dg_data[dg_descendant][rule_position][rule_type]["rules"]):
                                        if obj_name in dg_data[dg_descendant][rule_position][rule_type]["rules"][rule][addr_location]:
                                            # rule found
                                            rule_quoted = "\"" + rule + "\""
                                            if len(dg_data[dg_descendant][rule_position][rule_type]["rules"][rule][
                                                       addr_location]) == 1:
                                                # last item in rule, rule must be removed.
                                                del dg_data[dg_descendant][rule_position][rule_type]["rules"][rule]
                                                if dg_descendant == "shared":
                                                    file.write(
                                                        "reference removal for " + obj_name + " - " + dg_name + ": delete shared " + rule_position + " " + rule_type + " rules " + rule_quoted + "\n")
                                                else:
                                                    file.write(
                                                        "reference removal for " + obj_name + " - " + dg_name + ": delete device-group " + dg_descendant_quoted + " " + rule_position + " " + rule_type + " rules " + rule_quoted + "\n")

                                            else:
                                                # delete rule src or dst...
                                                dg_data[dg_descendant][rule_position][rule_type]["rules"][rule][addr_location].remove(obj_name)
                                                if dg_descendant == "shared":
                                                    file.write(
                                                        "reference removal for " + obj_name + " - " + dg_name + ": delete shared " + rule_position + " " + rule_type + " rules " + rule_quoted + " " + addr_location + " " + obj_name + "\n")
                                                else:
                                                    file.write(
                                                        "reference removal for " + obj_name + " - " + dg_name + ": delete device-group " + dg_descendant_quoted + " " + rule_position + " " + rule_type + " rules " + rule_quoted + " " + addr_location + " " + obj_name + "\n")

    return used_object


def analyse_object_values(dg_data: dict, file):
    obj_types_single_val = ["fqdn", "address"]
    for obj_type in obj_types_single_val:
        obj_typeval_name = obj_type + "_values"
        for val_key in dg_data[obj_typeval_name]:
            if obj_type == "fqdn":
                new_obj_name = "fqdn_" + val_key
            elif "-" in val_key:
                new_obj_name = val_key.replace("-","_")
                new_obj_name = "r_" + new_obj_name
            elif "/" not in val_key or "/32" in val_key:
                new_obj_name = val_key.replace("/32","")
                new_obj_name = "h_" + new_obj_name
            elif "/" in val_key:
                new_obj_name = val_key.replace("/", "_")
                new_obj_name = "n_" + new_obj_name

            if len(dg_data[obj_typeval_name][val_key]) > 1:
                for dg in dg_data[obj_typeval_name][val_key]:
                    dg_quoted = "\"" + dg + "\""
                    if dg_data[obj_typeval_name][val_key][dg] != new_obj_name:
                        cli = "rename device-group " + dg_quoted + " address " + dg_data[obj_typeval_name][val_key][dg] + " to " + new_obj_name
                    else:
                        cli = "no change needed..."
                    print("multiplied values: ", obj_typeval_name, val_key, dg, dg_data[obj_typeval_name][val_key][dg])
                    file.write("multiplied values: " + obj_typeval_name + "," + val_key + "," + dg + "," + dg_data[obj_typeval_name][val_key][dg] + " : " + cli + "\n")


def main(argv):

    file_path = 'C:/Users/dakos/Downloads/'
    xml_input = file_path + '16806.xml'
    #xml_output = xml_input.replace('.xml', '_mod.xml')
    time_str = time.strftime("%Y%m%d_%H%M%S")

    unused_addresses_file = file_path + 'paloalto_unused_addresses_' + time_str + '.txt'
    not_resolvable_fqdns_file = file_path + 'paloalto_notresolvable_fqdns_' + time_str + '.txt'
    multiplied_addresses_file = file_path + 'paloalto_multiplied_addresses_' + time_str + '.txt'
    unused_address_groups_file = file_path + 'paloalto_unused_address_groups_' + time_str + '.txt'
    multiplied_address_values_file = file_path + 'paloalto_multiplied_address_values_' + time_str + '.txt'

    # prepare the output file
    f_unused_addrs = open(unused_addresses_file, "x")
    f_unres_fqdns = open(not_resolvable_fqdns_file, "x")
    f_multiplied_addrs = open(multiplied_addresses_file, "x")
    f_unused_ags = open(unused_address_groups_file, "x")
    f_multiplied_addr_vals = open(multiplied_address_values_file, "x")

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
    extract_address_group_in_rules(dg_data)
    pdb.set_trace()

    # check how many times same value exist with different object names
    dg_data_values = collect_obj_values(element_root, ro_element)
    analyse_object_values(dg_data_values, f_multiplied_addr_vals)

    # addr_type can be fqdn or address. fqdn is just fqdn address contains fqdn, ip-address, ip-range
    addr_type = "fqdn"
    # find multiplied objects and not used objects
    for dg in dg_data:
        print("----------------------------------- ", dg, " ----------------------------------")
        dg_quoted = "\"" + dg + "\""
        dup_count = 0
        not_used_count = 0
        not_resolved_count = 0

        for address_object in dg_data[dg][addr_type]:
            address_object_quoted = "\"" + address_object + "\""
            if address_object in dg_data[dg]["rulebase-addr_flat"]:
                used_address = True
            else:
                used_address = False
            for dg_descendant in dg_data[dg]["descendants"]:
                if used_address is False and address_object in dg_data[dg_descendant]["rulebase-addr_flat"]:
                    used_address = True
                if address_object in dg_data[dg_descendant][addr_type]:
                    dup_count += 1
                    dg_descendant_quoted = "\"" + dg_descendant + "\""
                    f_multiplied_addrs.write("duplicated_" + addr_type + "_name " + address_object_quoted + " from_dg " + dg_quoted + " in " + dg_descendant_quoted + "\n")
            if used_address is False:
                not_used_count += 1
                f_unused_addrs.write("not_used_" + addr_type + ": delete device-group " + dg_quoted + " address " + address_object_quoted + "\n")

        if "fqdn" == addr_type:
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
                    fqdn_quoted = "\"" + fqdn_list[0] + "\""

                    obj_used = find_reference_for_object(dg_data, dg, fqdn_list[0], addr_type, f_unres_fqdns)
                    # final step is to remove the fqdn object itself
                    f_unres_fqdns.write(
                        "not_resolvable_fqdn: delete device-group " + dg_quoted + " address " + fqdn_quoted + "\n")

        print("sum for device-group:", dg_quoted, ":", "duplicated: ", dup_count, "not_used:", not_used_count, "unresolved:", not_resolved_count)

if __name__ == "__main__":
    main(sys.argv[1:])
