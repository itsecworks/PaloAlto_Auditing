#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script finds rules with too many services.
#
import pdb
import xml.etree.ElementTree as ET
import time
import json

file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '7106.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'rules_with_too_many_services' + time_str + '.csv'
service_count_limit = 6

def get_parent_leaf(dg_name, parent_list=None):

    if parent_list is None:
        parent_list = []
    if dg_name == "shared":
        return
    ro_dg = ro_element.find("./devices/entry/device-group/entry[@name='" + dg_name + "']")
    if ro_dg.find("./parent-dg") is not None:
        parent_dg_name = ro_dg.find("./parent-dg").text
        parent_list.append(parent_dg_name)
        return get_parent_leaf(parent_dg_name, parent_list)
    else:
        parent_list.append("shared")
    return parent_list

def get_service_count(dg_name, service_name):

    if dg_name == "shared":
        dg_path_list = ["shared"]
    else:
        dg_path_list = get_parent_leaf(dg_name)
        dg_path_list.insert(0, dg_name)
    for dg_name1 in dg_path_list:
        if dg_name1 == "shared":
            dg_svc_grps = root.findall("./shared/service-group/entry")
        else:
            dg_svc_grps = root.findall("./devices/entry/device-group/entry[@name='" + dg_name1 + "']/service-group/entry")
        for entry in dg_svc_grps:
            svc_grp_name = entry.attrib["name"]
            if svc_grp_name == service_name:
                services_count = len(entry.find("./members"))
                return services_count


tree = ET.parse(xml_input)
root = tree.getroot()
ro_element = root.find("./readonly")
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
result = ''

for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        for rule_pos in ["pre-rulebase", "post-rulebase"]:
            rulebase = dg.find("./" + rule_pos)
            if rulebase is not None:
                for rule_type in rulebase:
                    if rule_type.tag not in ["application-override","tunnel-inspection"]:
                        if rule_type.findall("./rules/entry") is not None:
                            for rule in rule_type.findall("./rules/entry"):
                                rule_name = rule.attrib["name"]
                                if rule_name not in ["intrazone-default", "interzone-default"]:
                                    if rule.find("./service") is not None:
                                        services_count = len(rule.find("./service"))
                                        for element in rule.findall("./service/member"):
                                            service_name = element.text
                                            service_count = get_service_count(dg_name, element.text)
                                            if service_count:
                                                services_count += service_count - 1

                                        if services_count > service_count_limit:
                                            result += "{c1},{c2},{c3},{c4},{c5},{c6}\n".format(c1=dg_name,
                                                                                             c2=rule_type.tag,
                                                                                             c3=rule_pos, c4=rule_name,
                                                                                             c5="service_count_over_limit",
                                                                                             c6=services_count)
                                    else:
                                        result += "{c1},{c2},{c3},{c4},{c5},{c6}\n".format(c1=dg_name, c2=rule_type.tag,
                                                                                         c3=rule_pos, c4=rule_name,
                                                                                         c5="no_service_found",
                                                                                         c6=0)
with open(result_output, 'w') as fp:
    fp.write(result)