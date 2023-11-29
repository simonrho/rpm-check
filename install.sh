#!/bin/sh
  
# ANSI escape code for bold and blue text
BLUE_BOLD="\033[1;34m"
# ANSI escape code to reset text style
RESET="\033[0m"

SCRIPT_NAME="rpm-check"

echo ""
echo -e "Starting the installation of the Juniper ${BLUE_BOLD}RPM Check${RESET} script...\n"

# Step 1: Download the jsi-cli script
curl -k -s https://raw.githubusercontent.com/simonrho/${SCRIPT_NAME}/main/${SCRIPT_NAME}.py -o /var/db/scripts/event/${SCRIPT_NAME}.py
echo -e "1. The ${BLUE_BOLD}${SCRIPT_NAME}${RESET} script has been successfully downloaded."

# Step 2: Register the jsi-cli script in the system
MY_USER=$(ls /var/home | head -n 1)

COMMANDS=$(cat <<EOF
edit
set system scripts language python3
set event-options event-script file ${SCRIPT_NAME}.py python-script-user ${MY_USER}
commit and-quit
EOF
)

echo -e "User '${BLUE_BOLD}${MY_USER}${RESET}' is used as event script user"

# Convert the multi-line string into a single line string
COMMANDS_ONE_LINE=$(echo "$COMMANDS" | tr '\n' ';')

# Ensure the last command doesn't end with an unnecessary semicolon
COMMANDS_ONE_LINE=${COMMANDS_ONE_LINE%;}

# Use the concatenated command string
/usr/sbin/cli -c "$COMMANDS_ONE_LINE" > /dev/null

echo -e "2. The ${BLUE_BOLD}${SCRIPT_NAME}${RESET} script has been successfully registered in the system.\n"

# Final message
echo -e "Installation complete!"
echo -e "Please check /var/log/${SCRIPT_NAME}.log to check the '${BLUE_BOLD}${SCRIPT_NAME}${RESET}' script log.\n"
