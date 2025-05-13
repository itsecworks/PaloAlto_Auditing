#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script finds rules with logging types.
# for a security rule the log at session end is by default enabled and it is not presented in the configuration.
# Only can be seen if it is disabled and re-enabled.
#
import os
import xml.etree.ElementTree as ET
import time
from xml.etree.ElementTree import Element


def getname(element: Element) -> str:

    if element.attrib is not None and "name" in element.attrib:
        element_name: str = element.attrib["name"]
    else:
        element_name = element.text
    return element_name


# Function to find all ancestors for a device-group recursively
def find_ancestors(ro_element, child_dg_name):

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


def get_xml_files(f_path):

    xml_list = []
    for filename in os.listdir(f_path):
        if filename.endswith("14281.xml"):
            xml_list.append(os.path.join(f_path,filename))
    return xml_list


def rule_log_audit(rule_base: Element, rule_position: str, devg_name: str, devg_ancestors: str) -> str:
    """

    :param devg_ancestors:
    :param rule_base:
    :param rule_position:
    :param devg_name:
    :return:
    """
    output_csv = ""
    result = {"no_log_start": 0, "log_start": 0, "no_log_end": 0, "log_end": 0, "no_log_fwd": 0}
    if rule_base is not None:
        if rule_base.findall("./security/rules/entry") is not None:
            for rule in rule_base.findall("./security/rules/entry"):
                rule_name = rule.attrib["name"]
                if rule.find("./log-start") is None or rule.find("./log-start").text == "no":
                    result["no_log_start"] += 1
                    output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}\n".format(c0=devg_ancestors,
                                                                          c1=devg_name,
                                                                          c2=rule_position,
                                                                          c3="no_log_start",
                                                                          c4=rule_name)
                else:
                    result["log_start"] += 1
                    output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}\n".format(c0=devg_ancestors,
                                                                          c1=devg_name,
                                                                          c2=rule_position,
                                                                          c3="log_start",
                                                                          c4=rule_name)
                # if log at session end is not present then it is on by default
                if rule.find("./log-end") is None or rule.find("./log-end").text == "yes":
                    result["log_end"] += 1
                    output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}\n".format(c0=devg_ancestors,
                                                                          c1=devg_name,
                                                                          c2=rule_position,
                                                                          c3="log_end",
                                                                          c4=rule_name)
                else:
                    result["no_log_end"] += 1
                    output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}\n".format(c0=devg_ancestors,
                                                                          c1=devg_name,
                                                                          c2=rule_position,
                                                                          c3="no_log_end",
                                                                          c4=rule_name)
                if rule.find("./log-setting") is not None:
                    lfp_name = rule.find("./log-setting").text
                    if lfp_name not in result:
                        result[lfp_name] = 1
                    else:
                        result[lfp_name] += 1
                else:
                    output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}\n".format(c0=devg_ancestors,
                                                                          c1=devg_name,
                                                                          c2=rule_position,
                                                                          c3="no_log_fwd",
                                                                          c4=rule_name)
                    result["no_log_fwd"] += 1

    for log_setting_key in result:
        output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}\n".format(c0=devg_name,
                                                              c1=rule_position,
                                                              c2=log_setting_key,
                                                              c3="NA",
                                                              c4=result[log_setting_key])

        output_csv += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}\n".format(c0=devg_ancestors,
                                                              c1=devg_name,
                                                              c2=rule_position,
                                                              c3=log_setting_key,
                                                              c4="NA",
                                                              c5=result[log_setting_key])
    return output_csv


time_str = time.strftime("%Y%m%d_%H%M%S")
file_path = 'C:/Users/dakos/Downloads/'
xml_files = get_xml_files(file_path)
result_output = file_path + 'paloalto_logging_audit_' + time_str + '.csv'
result_csv = "dg_ancestors, device-group_or_hostname+vsys, rule_position,log_setting, rulename, sum\n"

for fullpath_config in xml_files:

    if os.path.getsize(fullpath_config) > 0 and ".xml" in fullpath_config:

        tree = ET.parse(fullpath_config)
        root = tree.getroot()
        if root.find("./panorama") is not None:
            print("its a panorama configuration...")
            readonly_element: Element | None = root.find("./readonly")
            pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}

            for key in pa_all_dgs:
                xpath = pa_all_dgs[key]
                for dg in root.findall(xpath):
                    if key == "default":
                        dg_name = dg.attrib["name"]
                    else:
                        dg_name = key

                    dg_ancestors = find_ancestors(readonly_element, dg_name)
                    dg_anc_str = '|'.join(dg_ancestors)
                    for rule_pos in ["pre-rulebase", "post-rulebase"]:
                        rulebase = dg.find("./" + rule_pos)
                        result_csv += rule_log_audit(rulebase, rule_pos, dg_name, dg_anc_str)


        else:
            print("its a firewall configuration")
            rule_pos = "rulebase"
            hostname = root.find("./devices/entry/deviceconfig/system/hostname").text
            for vsys_xml in root.findall("./devices/entry/vsys/entry"):
                vsys_id = getname(vsys_xml)
                dev_name = hostname + "+" + vsys_id
                rulebase = vsys_xml.find("./" + rule_pos)
                result_csv += rule_log_audit(rulebase, rule_pos, dev_name)

with open(result_output, 'w') as fp:
    fp.write(result_csv)
