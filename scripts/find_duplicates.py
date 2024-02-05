#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Author: Ist wurst...
#
# Description:
# -------------
# This script find the duplicated objects within the panorama device-group hierarchy without the shared.
# it checks addresses in each device group one by one and check if the address exist in any child dg.
# If yes, it removes the address in child.
#
import xml.etree.ElementTree as ET
import time


file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '6308.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'duplicated_objects_' + time_str + '.txt'


def get_all_parents(ro_element):

    # a dictionary with key as a parent dg and value as all dg that parent dg is the one in the key.
    dg_parents = {}
    dg_parents["shared"] = []
    for dg in ro_element.findall("./devices/entry/device-group/entry"):
        dg_name = dg.attrib["name"]
        dg_parents["shared"].append(dg_name)
        if dg.find("./parent-dg") is not None:
            parent_dg_name = dg.find("./parent-dg").text
            if parent_dg_name not in dg_parents:
                dg_parents[parent_dg_name] = [dg_name]
            else:
                dg_parents[parent_dg_name].append(dg_name)

    return (dg_parents)


def get_all_children(dg_name, dg_parents, dg_child_list):


    if dg_name in dg_parents:
        dg_child_list += dg_parents[dg_name]
        if dg_name != "shared":
            for child_dg in dg_parents[dg_name]:
                get_all_children(child_dg, dg_parents, dg_child_list)
    return dg_child_list


def comp_element(element1, element2):


    # no more child if len = 0
    if len(element1) == 0:
        if element1.text != element2.text:
            print('no match on element with tag for value ', element1.tag, element1.text, element2.text)
            return False
        else:
            return True
    else:
        for subelement1 in element1:
            xpath = './' + subelement1.tag
            if len(subelement1) == 0:
                if element2.findall(xpath) is not None:
                    match = False
                    for entry2 in element2.findall(xpath):
                        if subelement1.text == entry2.text:
                            #full match on subelement without attributes
                            match = True
                            break
                    if not match:
                        #print('no match on element with tag for value ', element1.attrib["name"], subelement1.tag, subelement1.text)
                        return False
                    else:
                        return True
            else:
                if element2.find(xpath) is not None:
                    subelement2 = element2.find(xpath)
                    return comp_element(subelement1, subelement2)
                else:
                    #print('no subelement found on element2 ', element1.attrib["name"], subelement1, element2)
                    return False


result = ''
pa_object = 'address'

tree = ET.parse(xml_input)
root = tree.getroot()
ro_element = root.find("./readonly")
dg_parents = get_all_parents(ro_element)

pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        my_ch_list = []
        dg_all_child_names = get_all_children(dg_name, dg_parents, my_ch_list)
        xpath = "./" + pa_object + "/entry"
        dg_objects = dg.findall(xpath)

        if dg_objects is not None:
            for dg_obj in dg_objects:
                dg_obj_name = dg_obj.attrib["name"]

                if len(dg_all_child_names) > 0:
                    for ch_dg_name in dg_all_child_names:
                        ch_dg = root.find("./devices/entry/device-group/entry[@name='" + ch_dg_name + "']")
                        ch_dg_objects = ch_dg.findall(xpath)
                        if ch_dg_objects is not None and len(ch_dg_objects) > 0:
                            for ch_dg_obj in ch_dg_objects:
                                ch_dg_obj_name = ch_dg_obj.attrib["name"]
                                if dg_obj_name == ch_dg_obj_name:
                                    dg_obj_str = ET.tostring(dg_obj).decode().strip().replace(' ', '')
                                    ch_dg_obj_str = ET.tostring(ch_dg_obj).decode().strip().replace(' ', '')
                                    if dg_obj_str == ch_dg_obj_str:
                                        result += 'object string full match,' + ','.join(
                                            [dg_name, ch_dg_name, dg_obj_name]) + '\n'
                                        xpath_remove = "./devices/entry/device-group/entry[@name='" + ch_dg_name + "']/address"
                                        root.find(xpath_remove).remove(ch_dg_obj)
                                    elif comp_element(ch_dg_obj, dg_obj):
                                        result += 'object full match on every element with parent,' + ','.join(
                                            [dg_name, ch_dg_name, dg_obj_name]) + '\n'
                                        xpath_remove = "./devices/entry/device-group/entry[@name='" + ch_dg_name + "']/address"
                                        root.find(xpath_remove).remove(ch_dg_obj)
                                    else:
                                        result += 'just object name match,' + ','.join([dg_name, ch_dg_name, dg_obj_name]) + '\n'

with open(result_output, 'w') as fp:
    fp.write(result)

xml_str = ET.tostring(root)
with open(xml_output, 'wb') as f:
    f.write(xml_str)