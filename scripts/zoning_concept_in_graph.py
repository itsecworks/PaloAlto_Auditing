#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script creates for each device-group a chord chart from the rulebase
# TODO: add chart the way that a complete device-group hierarcy is covered. Currently dg level separation used only
#

import xml.etree.ElementTree as ET
# Load d3blocks
from d3blocks import D3Blocks
import pandas as pd


file_path = 'C:/Users/akdaniel/Downloads/'
xml_input = file_path + 'running-config.xml'

tree = ET.parse(xml_input)
root = tree.getroot()

for dg in root.findall("./devices/entry/device-group/entry"):
    fromto = {}
    dg_name = dg.attrib["name"]
    print(dg_name)
    for rule_pos in ['pre-rulebase', 'post-rulebase']:
        rulebase = dg.findall("./" + rule_pos + "/security/rules/entry")
        if rulebase is not None:
            for rule in rulebase:
                rule_name = rule.attrib["name"]
                for fromzone in rule.findall("./from/member"):
                    #if fromzone.text != 'any':
                    for tozone in rule.findall("./to/member"):
                            #if tozone.text != 'any':
                        key = fromzone.text + '_to_' + tozone.text
                        if key in fromto:
                            fromto[key] += 1
                        else:
                            fromto[key] = 1
    if fromto:
        source = []
        target = []
        weight = []
        for key in fromto:
            source.append(key.split('_to_')[0])
            target.append(key.split('_to_')[1])
            weight.append(fromto[key])
        data = {'source': source,
                'target': target,
                'weight': weight
                }
        df = pd.DataFrame(data)
        # Initialize
        d3 = D3Blocks()
        # specify the output path and plot
        file = 'c:/temp/chord_' + dg_name + '.html'
        d3.chord(df, filepath=file)