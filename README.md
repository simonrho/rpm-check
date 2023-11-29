# RPM Monitoring Script

## Overview
This Python script is a Junos event script designed to monitor RPM (Real-time Performance Monitoring) status for verifying the operational status of a routing-instance. It is particularly useful in ensuring that core-facing routing-instances function as expected. Upon detecting specific conditions, the script can trigger the Junos system to execute predefined commands or actions.

## Features
 - Monitors RPM probe results.
 - Checks the operational status of routing-instances based on RPM.
 - Executes customized Junos CLI commands based on pass or fail conditions.
 - Tabulates and logs RPM test results for easy analysis.
 - Rotates log files to manage disk space usage.

## Installation
 To install the script, run the following command in your shell:

 ```
 start shell command "curl -k -s https://raw.githubusercontent.com/simonrho/rpm-check/main/install.sh | /bin/sh"
 
 ```

### Installation output sample
```sh
root@alpha> start shell command "curl -k -s https://raw.githubusercontent.com/simonrho/rpm-check/main/install.sh | /bin/sh"    

Starting the installation of the Juniper RPM Check script...

1. The rpm-check script has been successfully downloaded.
User 'mist' is used as event script user
2. The rpm-check script has been successfully registered in the system.

Installation complete!
Please check /var/log/rpm-check.log to check the 'rpm-check' script log.
```

Alternatively, copy the rpm-check.py file to the /var/db/scripts/event directory on your Junos system. Then, apply the following configurations:

```
set event-options event-script file rpm-check.py python-script-user add-your-local-user-name
```

### Arguments
 - `rpm-owner`: Specifies the owner of the RPM probe.
 - `pass-threshold`: Sets the threshold for a pass condition (default: 30.0%).
 - `fail-threshold`: Sets the threshold for a fail condition (default: 100.0%).
 - `pass-command`: CLI command to execute upon passing. `$routing-instance-name` is a placeholder for the routing-instance-name.
 - `fail-command`: CLI command to execute upon failing. `$routing-instance-name` is a placeholder for the routing-instance-name.

## Logging
 - The script logs detailed information in `/var/log/rpm-check.log`.
 - Log files are rotated upon reaching a size of 10 MB with up to 3 backups.

## Config Example
```cpp
services {
    rpm {
        probe bng-cp {
            test test1 {
                probe-type icmp-ping;
                target address 8.8.8.8;
                probe-count 3;
                probe-interval 3;
                test-interval 3;
                routing-instance mgmt_junos;
                thresholds {
                    successive-loss 3;
                }
            }
            test test2 {
                probe-type icmp-ping;
                target address 8.8.4.4;
                probe-count 3;
                probe-interval 3;
                test-interval 3;
                routing-instance mgmt_junos;
                thresholds {
                    successive-loss 3;
                }
            }
        }
    }
}

event-options {
    generate-event {
        every-1min time-interval 60;
    }
    policy generate-core-down-on-ping-failure {
        events ping_probe_failed;       
        within 3 {
            trigger after 1;
        }
        then {
            event-script rpm-check.py {
                arguments {
                    rpm-owner bng-cp;
                    fail-threshold 100;
                    fail-command "show dhcp relay statistics routing-instance $routing-instance-name";
                }
            }
        }
    }
    policy generate-core-up-on-ping-success {
        events every-1min;
        then {
            event-script rpm-check.py {
                arguments {
                    rpm-owner bng-cp;
                    pass-threshold 30;
                    pass-command "show dhcp server statistics routing-instance $routing-instance-name";
                }
            }
        }
    }
    event-script {
        file rpm-check.py {
            python-script-user add-your-local-user-name;
        }
    }
}
```

## Log file sample
```sh
2023-11-29 01:27:10,678 INFO 
2023-11-29 01:27:10,678 INFO ****************
2023-11-29 01:27:10,678 INFO rpm check ends
2023-11-29 01:27:10,678 INFO ****************
2023-11-29 01:27:10,679 INFO 
2023-11-29 01:28:08,863 INFO sys.argv: ['/var/db/scripts/event/rpm-check.py', '-rpm-owner', 'bng-cp', '-pass-threshold', '30', '-pass-command', 'show dhcp server statistics routing-instance $routing-instance-name']
2023-11-29 01:28:08,866 INFO ****************
2023-11-29 01:28:08,866 INFO rpm check starts
2023-11-29 01:28:08,867 INFO ****************
2023-11-29 01:28:08,867 INFO Input options:
2023-11-29 01:28:08,867 INFO   RPM Owner: "bng-cp"
2023-11-29 01:28:08,867 INFO   Pass Threshold: 30.0%
2023-11-29 01:28:08,868 INFO   Fail Threshold: 100.0%
2023-11-29 01:28:08,868 INFO   Pass Command: "show dhcp server statistics routing-instance $routing-instance-name"
2023-11-29 01:28:08,868 INFO   Fail Command: ""
2023-11-29 01:28:08,868 INFO 
2023-11-29 01:28:09,793 INFO *****************
2023-11-29 01:28:09,793 INFO rpm test results:
2023-11-29 01:28:09,794 INFO *****************
2023-11-29 01:28:09,794 INFO 
routing instance  test name  target address  status  reason           
----------------  ---------  --------------  ------  -----------------
mgmt_junos        test1      8.8.8.8         PASS    Response received
mgmt_junos        test2      8.8.4.4         PASS    Response received
2023-11-29 01:28:09,794 INFO 
2023-11-29 01:28:09,795 INFO ************************************************
2023-11-29 01:28:09,795 INFO routing-instance operational status based on RPM
2023-11-29 01:28:09,795 INFO pass threshold: 30.0%, fail threshold: 100.0%
2023-11-29 01:28:09,795 INFO ************************************************
2023-11-29 01:28:09,796 INFO 
routing instance  total count  pass count  fail count  pass percent  fail percent  status
----------------  -----------  ----------  ----------  ------------  ------------  ------
mgmt_junos        2            2           0           100.0%        0.0%          PASS  
2023-11-29 01:28:09,796 INFO 
2023-11-29 01:28:09,796 INFO ********************
2023-11-29 01:28:09,797 INFO CLI commands to run:
2023-11-29 01:28:09,797 INFO ********************
2023-11-29 01:28:09,797 INFO command for 'PASS' status of RI 'mgmt_junos': "show dhcp server statistics routing-instance mgmt_junos"
2023-11-29 01:28:10,647 INFO output:
Packets dropped:
    Total                      1640
    dhcp-service total         1640

Offer Delay:
    DELAYED                    0
    INPROGRESS                 0
    TOTAL                      0

Messages received:
    BOOTREQUEST                0
    DHCPDECLINE                0
    DHCPDISCOVER               0
    DHCPINFORM                 0
    DHCPRELEASE                0
    DHCPREQUEST                0
    DHCPLEASEQUERY             0
    DHCPBULKLEASEQUERY         0
    DHCPACTIVELEASEQUERY       0

Messages sent:
    BOOTREPLY                  0
    DHCPOFFER                  0
    DHCPACK                    0
    DHCPNAK                    0
    DHCPFORCERENEW             0
    DHCPLEASEUNASSIGNED        0
    DHCPLEASEUNKNOWN           0
    DHCPLEASEACTIVE            0
    DHCPLEASEQUERYDONE         0

2023-11-29 01:28:10,648 INFO 
2023-11-29 01:28:10,648 INFO ****************
2023-11-29 01:28:10,649 INFO rpm check ends
2023-11-29 01:28:10,649 INFO ****************
2023-11-29 01:28:10,649 INFO 
```