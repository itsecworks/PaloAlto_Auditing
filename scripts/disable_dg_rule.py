# -*- coding: utf-8 -*-
# Author: Ist wurst...
# this script disables the rule with the given name in the given device-group pre-rulebase.

import requests
import time
import urllib.parse
import re

# PAN-OS Firewall or Panorama details
PANORAMA_HOST = "https://192.168.2.210"  # Change this
API_KEY = "LUFRPT...XhXRUptYSsrZw=="     # Change this

# to get your key use this curl command
# -k is only needed in lab env to ignore certificate check
# curl -k -H "Content-Type: application/x-www-form-urlencoded" -X POST https://firewall/api/?type=keygen -d "user=<user>&password=<password>"

# Device group and rule info
DEVICE_GROUP = "america"
RULE_NAME = "testrule"

# Disable SSL warnings (not recommended for production)
requests.packages.urllib3.disable_warnings()


def get_rule():
    url = (
        f"{PANORAMA_HOST}/restapi/v10.2/Policies/SecurityPreRules"
        f"?location=device-group&device-group={DEVICE_GROUP}&name={RULE_NAME}"
    )
    headers = {
        "X-PAN-KEY": API_KEY
    }

    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        print(f"✅ Successfully fetched rule '{RULE_NAME}'.")
        rule_data = response.json()
        return rule_data
    else:
        print(f"❌ Failed to fetch rule. Status code: {response.status_code}")
        print("Response:", response.text)
        exit(1)


def is_rule_disabled(rule_data):
    rule_entry = rule_data.get("result", {}).get("entry", [])[0]
    disabled_status = rule_entry.get("disabled", "no")
    return disabled_status.lower() == "yes"


def put_rule(rule_data):
    rule_entry = rule_data.get("result", {}).get("entry", [])[0]
    if not rule_entry:
        print("❌ Rule entry not found in response.")
        exit(1)

    rule_entry["disabled"] = "yes"
    rule_entry["tag"] = {"member": ["unused-rule"]}

    url = (
        f"{PANORAMA_HOST}/restapi/v10.2/Policies/SecurityPreRules"
        f"?location=device-group&device-group={DEVICE_GROUP}&name={RULE_NAME}"
    )
    headers = {
        "Content-Type": "application/json",
        "X-PAN-KEY": API_KEY
    }

    payload = {
        "entry": rule_entry
    }

    response = requests.put(url, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        print(f"✅ Successfully updated (disabled) rule '{RULE_NAME}'.")
    else:
        print(f"❌ Failed to update rule. Status code: {response.status_code}")
        print("Response:", response.text)
        exit(1)


def commit_to_panorama():
    url = f"{PANORAMA_HOST}/api/?type=commit&cmd=<commit></commit>&key={API_KEY}"

    response = requests.post(url, verify=False)

    if response.status_code == 200:
        print("✅ Commit to Panorama started.")
        job_id = extract_job_id(response.text)
        return job_id
    else:
        print(f"❌ Failed to commit to Panorama. Status code: {response.status_code}")
        print("Response:", response.text)
        exit(1)


def push_to_device_group():
    cmd = (
        "<commit-all>"
        "<shared-policy>"
        "<device-group>"
        f"<entry name=\"{DEVICE_GROUP}\"/>"
        "</device-group>"
        "</shared-policy>"
        "</commit-all>"
    )
    encoded_cmd = urllib.parse.quote(cmd)

    url = f"{PANORAMA_HOST}/api/?type=commit&cmd={encoded_cmd}&key={API_KEY}"

    response = requests.post(url, verify=False)

    if response.status_code == 200:
        print(f"✅ Push to device-group '{DEVICE_GROUP}' started.")
        job_id = extract_job_id(response.text)
        return job_id
    else:
        print(f"❌ Failed to push to device-group. Status code: {response.status_code}")
        print("Response:", response.text)
        exit(1)


def extract_job_id(xml_text):
    match = re.search(r"<job>(\d+)</job>", xml_text)
    if match:
        return match.group(1)
    else:
        print("❌ Failed to extract job ID from response.")
        print(xml_text)
        exit(1)


def check_job_status(job_id):
    url = f"{PANORAMA_HOST}/api/?type=op&cmd=<show><jobs><id>{job_id}</id></jobs></show>&key={API_KEY}"

    while True:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            if "<status>FIN</status>" in response.text:
                if "<result>OK</result>" in response.text:
                    print(f"✅ Job {job_id} finished successfully.")
                else:
                    print(f"❌ Job {job_id} finished but not OK.")
                break
            else:
                print(f"ℹ️ Job {job_id} still running... waiting 5 seconds...")
                time.sleep(5)
        else:
            print(f"❌ Failed to check job status. Status code: {response.status_code}")
            print("Response:", response.text)
            exit(1)


if __name__ == "__main__":
    # Step 1: GET the rule
    rule_data = get_rule()

    # Step 2: Check if already disabled
    if is_rule_disabled(rule_data):
        print(f"ℹ️ Rule '{RULE_NAME}' is already disabled. No action needed.")
    else:
        # Step 3: Modify and PUT the rule
        put_rule(rule_data)

        # Step 4: Commit to Panorama
        panorama_job_id = commit_to_panorama()
        check_job_status(panorama_job_id)

        # Step 5: Push to Device Group
        push_job_id = push_to_device_group()
        check_job_status(push_job_id)
