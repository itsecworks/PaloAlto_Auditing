import argparse
import requests
from xml.etree.ElementTree import fromstring
import logging
import sys
import json
import datetime
import re
import socket
from collections import defaultdict

def get_api(device, params, log=False):
    # script_path = os.path.dirname(__file__)
    # CA_file = "Palo_Alto_Networks_Inc-Root-CA_G1.pem"
    # CA_path = os.path.join(script_path, CA_file)

    request_timeout = 20

    url: str = 'https://' + device + '/api/'

    if log:
        logging.info('Trying to access device: %s with cmd: %s', device, params['cmd'])
    try:
        # response = requests.post(url, timeout=request_timeout, verify=CA_path)
        response = requests.post(url, params=params, timeout=request_timeout, verify=False)
    except requests.exceptions.RequestException as e:
        if log:
            logging.error('We run in that problem: %s', e)
        raise SystemExit(e)

    if response.status_code != 200:
        if log:
            logging.error('with the url: %s', response.url)
            logging.error('Cannot access the website, status code: %s', response.status_code)
            logging.error('reply from the website:\n%s\n', response.text)
        raise SystemExit(str(response.status_code) + " - " + response.text)
    else:
        if log:
            logging.info('response from website:\n\n%s\n', response.text)
        return response.text


def validate_ip_address(address):
    match = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", address)

    if bool(match) is False:
        # print("IP address {} is not valid".format(address))
        return False

    for part in address.split("."):
        if int(part) < 0 or int(part) > 255:
            print("IP address {} is not valid".format(address))
            return False

    # print("IP address {} is valid".format(address))
    return True


def host_to_dns(device):
    if validate_ip_address(device):
        try:
            dnsname = socket.gethostbyaddr(device)[0]
            return dnsname
        except socket.error:
            return "not resolvable"

    else:
        try:
            socket.gethostbyname(device)
            return device
        except socket.error:
            return "not resolvable"


def find_old_rules(xml_string, threshold_months=1, days_per_month=30):
    # Parse the XML
    root = fromstring(xml_string)

    # Calculate threshold in seconds
    threshold_seconds = threshold_months * days_per_month * 24 * 60 * 60

    # Collect rules older than threshold
    old_rules = defaultdict(list)

    for rule in root.findall(".//rules/entry"):
        name = rule.attrib.get("name")
        last_hit = int(rule.findtext("last-hit-timestamp", default="0"))
        mod_time = int(rule.findtext("rule-modification-timestamp", default="0"))

        if last_hit == 0 or mod_time == 0:
            continue

        age_seconds = last_hit - mod_time
        if age_seconds > threshold_seconds:
            age_days = age_seconds // (24 * 60 * 60)
            age_months = age_days // days_per_month
            old_rules[age_months].append((name, age_days))

    return dict(sorted(old_rules.items()))


def output_parser_uptime(xml, xpath):

    print("for checking uptime and hitcount.. it comes later")
    return "nothing"

def main(argv):

    file_path = 'C:/Temp/'

    parser = argparse.ArgumentParser(description='Collect hit counter for security rules.',
                                     epilog="And that's how you use xml api...")

    parser.add_argument('-l', '--log',
                        action=argparse.BooleanOptionalAction,
                        default=False,
                        dest='log',
                        help='switch logging on or off')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s 1.0')

    parser.add_argument('-d', '--device',
                        dest='device',
                        help='IP or hostname of the Palo Alto Device (Panorama or Firewall',
                        default='10.1.1.1')

    parser.add_argument('-k', '--hashkey',
                        help='Password hash for the logon on Palo Alto Panorama',
                        dest='hashkey',
                        default='LUFRPT1...')

    parser.add_argument('-g', '--device-group',
                        dest='device_group',
                        help='Device-group name in Panorama. If this is not added, the script considers the device as a firewall.',
                        default='default_device_group',
                        required=False)

    args = parser.parse_args()
    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if host_to_dns(args.device) == "not resolvable":
        exit()
    else:
        device = host_to_dns(args.device)

    # First check if the device is a firewall or a panorama with checking the device-group argument
    # if its set other than default it's a hc request to panorama
    if args.device_group is not "default_device_group":
        print("panorama hc collector.. comes later...")
    # otherwise it is a hc request to a firewall.
    else:
        data_collector = {
            'rule_hit_counter': {
                'cmd': '<show><rule-hit-count><vsys><vsys-name><entry name=\'vsys1\'><rule-base><entry name=\'security\'><rules><all/></rules></entry></rule-base></entry></vsys-name></vsys></rule-hit-count></show>',
                'xpath': ['./result/rules/entry']
            },
            'uptime_counter': {
                'cmd': '<show><system><info></info></system></show>',
                'xpath': ['./result/system/uptime']
            },
        }

        for key in data_collector:

            if args.log:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = file_path + device + '_' + key + '_' + timestamp + '.log'
                logging.basicConfig(filename=filename, filemode='w',
                                    format='%(asctime)s - %(process)d - %(levelname)s - %(message)s', level=logging.INFO)

            cmd = data_collector[key]['cmd']
            xpath = data_collector[key]['xpath']
            params = {
                'type': 'op',
                'key': args.hashkey,
                'cmd': cmd
            }
            xml_response: str = get_api(device, params, args.log)

            data = {}
            if key == 'rule_hit_counter':
                data = find_old_rules(xml_response)
            elif key == 'uptime_counter':
                data["uptime"] = output_parser_uptime(xml_response, xpath)

            old_rules_result = find_old_rules(xml_response)
            for months, rules in old_rules_result.items():
                print(f"\nOn firewall {device} rules older than {months} month(s):")
                for rule_name, age_in_days in rules:
                    print(f" - {rule_name} (Age: {age_in_days} days)")

            with open(file_path + device + '_' + key + '.json', 'w') as fp:
                json.dump(data, fp)

if __name__ == "__main__":
    main(sys.argv[1:])
