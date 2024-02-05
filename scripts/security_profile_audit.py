#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the security rules and the security profile settings within panorama device-group hierarchy.
#
import pdb
import xml.etree.ElementTree as ET
import time

file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '6308.xml'
# xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'sec_profile_audit_' + time_str + '.csv'


def get_members_from_group(profile_data):

    profile_list = []
    for element in profile_data:
        profile_type = element.tag
        profile_value = element.find("./member").text
        profile_type_short = profile_type[0:3]
        profile_text = profile_type_short + "_" + profile_value
        profile_list.append(profile_text)
    profile_set = "+".join(profile_list)
    return profile_set


def find_parent_dg(dg_name):

    readonly_dg = readonly_node.find("./devices/entry/device-group/entry[@name='" + dg_name + "']")
    if readonly_dg.find("./parent-dg") is not None:
        parent_dg_name = readonly_dg.find("./parent-dg").text
        return parent_dg_name
    else:
        return "no-parent"


def find_object(obj_name, dg):
    if "name" in dg.attrib:
        dg_name = dg.attrib["name"]
    else:
        dg_name = "shared"
    obj_found = 'no'
    for spg in dg.findall("./profile-group/entry"):
        if spg.attrib["name"] == obj_name:
            obj_found = 'yes'
            return spg
    if obj_found == 'no':
        dg_name_pr = find_parent_dg(dg_name)
        if dg_name_pr == "no-parent":
            dg_new = root.find("./shared")
        else:
            dg_new = root.find("./devices/entry/device-group/entry[@name='" + dg_name_pr + "']")
        return find_object(obj_name, dg_new)


def sec_profile_check(dg_name, rulebase_xml, dg):

    result = ''
    c = 0
    dict_pgs = {}
    dict_pgs[dg_name] = {}
    sec_rules = rulebase_xml.find("./security/rules")
    rulebase_pos = rulebase_xml.tag
    if sec_rules is not None:
        for rule in sec_rules:
            # profile-setting exists
            if rule.find("./profile-setting"):
                # group used in profile setting
                if rule.find("./profile-setting/group"):
                    profile_group_name = rule.find("./profile-setting/group/member").text
                    # find the spg through the dg hierarchy
                    profile_group_xml = find_object(profile_group_name, dg)
                    profile_set = get_members_from_group(profile_group_xml)

                    if profile_group_name not in dict_pgs[dg_name]:
                        dict_pgs[dg_name][profile_group_name] = {}
                        dict_pgs[dg_name][profile_group_name]["count"] = 1
                        dict_pgs[dg_name][profile_group_name]["set"] = profile_set
                    else:
                        dict_pgs[dg_name][profile_group_name]["count"] += 1
                # empty group or profiles used in profile setting
                elif (rule.find("./profile-setting/group") is not None and len(rule.find("./profile-setting/group")) == 0) or (rule.find("./profile-setting/profiles") is not None and len(rule.find("./profile-setting/profiles")) == 0):
                    rule_name = rule.attrib["name"]
                    action = rule.find("./action").text
                    if rule.find("./disabled") is not None:
                        disabled_state = rule.find("./disabled").text
                    else:
                        disabled_state = "no"
                    result += "{c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}\n".format(c1=dg_name, c2=rulebase_pos,
                                                                                 c3=rule_name, c4=action,
                                                                                 c5="no-profile-group2",
                                                                                 c6="no-profile-setting2",
                                                                                 c7=disabled_state)
                    c += 1

                # profiles used in profile setting
                else:
                    rule_name = rule.attrib["name"]
                    action = rule.find("./action").text
                    if rule.find("./disabled") is not None:
                        disabled_state = rule.find("./disabled").text
                    else:
                        disabled_state = "no"

                    profile_xml = rule.find("./profile-setting/profiles")
                    profile_set = get_members_from_group(profile_xml)

                    if profile_set not in dict_pgs[dg_name]:
                        dict_pgs[dg_name][profile_set] = {}
                        dict_pgs[dg_name][profile_set]["count"] = 1
                        dict_pgs[dg_name][profile_set]["set"] = profile_set
                    else:
                        dict_pgs[dg_name][profile_set]["count"] += 1
                    result += "{c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}\n".format(c1=dg_name, c2=rulebase_pos,
                                                                                 c3=rule_name, c4=action,
                                                                                 c5="no-profile-group",
                                                                                 c6=profile_set,
                                                                                 c7=disabled_state)

            # no profile-setting at all
            else:
                rule_name = rule.attrib["name"]
                action = rule.find("./action").text
                if rule.find("./disabled") is not None:
                    disabled_state = rule.find("./disabled").text
                else:
                    disabled_state = "no"
                result += "{c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}\n".format(c1=dg_name, c2=rulebase_pos,
                                                                             c3=rule_name, c4=action,
                                                                             c5="no-profile-group",
                                                                             c6="no-profile-setting",
                                                                             c7=disabled_state)
                c += 1

        # counter for rules without profile-setting
        result += "{c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}\n".format(c1=dg_name, c2=rulebase_pos,
                                                                     c3="NA", c4="NA",
                                                                     c5="no-profile-group",
                                                                     c6="no-profile-setting",
                                                                     c7="NA", c8=str(c))

        # counter for groups in profile-setting
        for spg in dict_pgs[dg_name]:
            result += "{c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}\n".format(c1=dg_name, c2=rulebase_pos,
                                                                         c3="NA", c4="NA",
                                                                         c5=spg,
                                                                         c6=str(dict_pgs[dg_name][spg]["set"]),
                                                                         c7="NA",c8=str(dict_pgs[dg_name][spg]["count"]))

    return result


tree = ET.parse(xml_input)
root = tree.getroot()
readonly_node = root.find("./readonly")

result = ''
rule_pos_list = ["pre", "post"]
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        for rule_pos in rule_pos_list:
            xpath_rulebase = "./" + rule_pos + "-rulebase"
            dg_rulebase = dg.find(xpath_rulebase)
            if dg_rulebase is not None:
                result += sec_profile_check(dg_name, dg_rulebase, dg)

with open(result_output, 'w') as fp:
    fp.write(result)