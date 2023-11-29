#!/usr/bin/env python3

import os
import stat
import sys
import argparse
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from lxml import etree
from io import StringIO

log_file = '/var/log/rpm-check.log'

log_buffer = StringIO()
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
stream_handler = logging.StreamHandler(log_buffer)
stream_handler.setFormatter(log_formatter)

logger = logging.getLogger('rpm-check-logger')
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler) 

class Tabulate:
    def __init__(self, table, headers):
        self.table = table
        self.headers = headers

    def format_row(self, row, col_widths):
        return '  '.join(f"{str(item).ljust(width)}" for item, width in zip(row, col_widths))

    def get_col_widths(self):
        widths = [len(str(header)) for header in self.headers]
        for row in self.table:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        return widths

    def create_table(self):
        col_widths = self.get_col_widths()
        header_row = self.format_row(self.headers, col_widths)
        separator = '  '.join('-' * width for width in col_widths)
        rows = [self.format_row(row, col_widths) for row in self.table]
        return '\n'.join([header_row, separator] + rows)

    def __str__(self):
        return self.create_table()


def run_cli_command(command, format='xml'):
    def remove_namespaces(xml_text):
        root = etree.fromstring(xml_text)

        for elem in root.getiterator():
            if not hasattr(elem.tag, 'find'):
                continue
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i + 1:]

        for elem in root.iter():
            elem.attrib.clear()

        etree.cleanup_namespaces(root)

        return etree.tostring(root).decode('utf-8')

    try:        
        if format == 'xml':
            result = subprocess.run(f'/usr/sbin/cli -c "{command} | display xml"', shell=True, text=True, capture_output=True, check=True)
            r = remove_namespaces(result.stdout)
            return etree.fromstring(r)
        else:
            result = subprocess.run(f'/usr/sbin/cli -c "{command}"', shell=True, text=True, capture_output=True, check=True)
            return result.stdout
        
    except subprocess.CalledProcessError as e:
        logger.error(f"An error occurred: {e}")
        return None


def main(): 
    logger.info(f'sys.argv: {sys.argv}')

    parser = argparse.ArgumentParser(description='Script to monitor RPM status and execute commands based on thresholds.')

    parser.add_argument('-rpm-owner', '--rpm-owner', type=str, required=True, dest='owner', help='Owner of the probe')
    parser.add_argument('-pass-threshold', '--pass-threshold', type=float, default=30.0, dest='pass_threshold', help='Pass threshold value (default: 30.0)')
    parser.add_argument('-fail-threshold', '--fail-threshold', type=float, default=100.0, dest='fail_threshold', help='Fail threshold value (default: 100.0)')
    parser.add_argument('-pass-command', '--pass-command', type=str, default="", dest='pass_command', help='Command to execute upon success ($routing-instance-name serves as a placeholder for the routing-instance-name)')
    parser.add_argument('-fail-command', '--fail-command', type=str, default="", dest='fail_command', help='Command to execute upon failed ($routing-instance-name serves as a placeholder for the routing-instance-name).')

    args = parser.parse_args()

    owner = args.owner
    pass_threshold = args.pass_threshold
    fail_threshold = args.fail_threshold
    pass_command = args.pass_command.replace('"', '\\"')
    fail_command = args.fail_command.replace('"', '\\"')

    logger.info('****************')
    logger.info('rpm check starts')
    logger.info('****************')

    logger.info(f"Input options:")
    logger.info(f'  RPM Owner: "{owner}"')
    logger.info(f"  Pass Threshold: {pass_threshold}%")
    logger.info(f"  Fail Threshold: {fail_threshold}%")
    logger.info(f'  Pass Command: "{pass_command}"')
    logger.info(f'  Fail Command: "{fail_command}"')
    logger.info('')

    command = f'show services rpm probe-results owner {owner}'
    root = run_cli_command(command)

    probes = { 'owner': owner, 'rpms': {} }
    for probe_results in root.findall(f".//probe-test-results[owner='{owner}']"):
        owner = probe_results.find('owner').text
        test_name = probe_results.find('test-name').text
        target_address = probe_results.find('target-address').text
        routing_instance_name = probe_results.find('routing-instance-name').text
        probe_status = probe_results.find('.//probe-single-results/probe-status').text

        probe_list = probes.get('rpms').get(routing_instance_name, {})

        if not probe_list:
            probes.get('rpms').update({
                routing_instance_name: { 
                    'total-count': 0, 
                    'pass-count': 0, 
                    'fail-count': 0,
                    'pass-percent': 0.0, 
                    'fail-percent': 0.0, 
                    'probes': []
                }
            })

        probe_dict = {
            'test-name': test_name,
            'target-address': target_address,
            'status': probe_status == 'Response received',
            'reason': probe_status,
        }

        ri = probes.get('rpms').get(routing_instance_name)


        ri['total-count'] += 1
        if probe_dict['status']:
            ri['pass-count'] += 1
        else:
            ri['fail-count'] += 1

        ri['pass-percent'] = ri['pass-count']*100./ri['total-count']
        ri['fail-percent'] = ri['fail-count']*100./ri['total-count']
        ri['probes'].append(probe_dict)


    action_commands = []
    rpm_status_table = []
    ri_status_table = []
    for ri_name, probe_result in probes.get('rpms').items():
        if probe_result['pass-percent'] >= pass_threshold:
            probe_result['status'] = 'PASS'
            action_commands.append({
                'status': probe_result['status'],
                'ri': ri_name,
                'command': pass_command.replace('$routing-instance-name', ri_name),
            })
        elif probe_result['fail-percent'] >= fail_threshold:
            probe_result['status'] = 'FAIL'
            action_commands.append({
                'status': probe_result['status'],
                'ri': ri_name,
                'command': fail_command.replace('$routing-instance-name', ri_name),
            })

        ri_status_table.append([
            ri_name, 
            probe_result['total-count'],
            probe_result['pass-count'],
            probe_result['fail-count'],
            f"{probe_result['pass-percent']}%",
            f"{probe_result['fail-percent']}%",
            probe_result['status'],
        ])

        for probe in probe_result.get('probes'):
            row = [ri_name]
            row.append(probe.get('test-name'))
            row.append(probe.get('target-address'))
            row.append('PASS' if probe.get('status') else 'FAIL')
            row.append(probe.get('reason'))
            rpm_status_table.append(row)

    logger.info('*****************')
    logger.info('rpm test results:')
    logger.info('*****************')
    headers = ["routing instance", "test name", "target address", "status", "reason"]
    tabulated_table = Tabulate(rpm_status_table, headers)
    logger.info(f"\n{tabulated_table}")
    logger.info('')

    logger.info('************************************************')
    logger.info('routing-instance operational status based on RPM')
    logger.info(f'pass threshold: {pass_threshold}%, fail threshold: {fail_threshold}%')
    logger.info('************************************************')
    headers = ["routing instance", "total count", "pass count", "fail count", "pass percent", "fail percent", "status"]
    tabulated_table = Tabulate(ri_status_table, headers)
    logger.info(f"\n{tabulated_table}")
    logger.info('')


    logger.info('********************')
    logger.info('CLI commands to run:')
    logger.info('********************')
    for v in action_commands:
        try:
            command = v['command']
            if command:
                logger.info(f"command for '{v['status']}' status of RI '{v['ri']}': \"{command}\"")
                output = run_cli_command(command, format='text')  
                logger.info(f"output:\n{output}")
        except Exception as e:
            logger.error(f"{e.message}: {v['command']}")

    logger.info('')
    logger.info('****************')
    logger.info('rpm check ends')
    logger.info('****************')
    logger.info('')


if __name__ == "__main__":
    main()


if not os.path.exists(log_file):
    open(log_file, 'a').close()
    os.chmod(log_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
else:
    os.chmod(log_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)

with open(log_file, 'a') as f:
    f.write(log_buffer.getvalue())

