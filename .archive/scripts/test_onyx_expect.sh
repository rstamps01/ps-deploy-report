#!/usr/bin/expect -f
# Test script for Onyx interactive SSH commands

set timeout 30
set switch_ip [lindex $argv 0]
set password [lindex $argv 1]
set command [lindex $argv 2]

# Disable host key checking
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@$switch_ip

# Handle password prompt
expect {
    "Password:" {
        send "$password\r"
    }
    timeout {
        puts "ERROR: Timeout waiting for password prompt"
        exit 1
    }
}

# Wait for the command prompt (look for ">" or "#")
expect {
    -re {\[.*\] >} {
        # Send the command
        send "$command\r"
    }
    timeout {
        puts "ERROR: Timeout waiting for command prompt"
        exit 1
    }
}

# Wait for command output and next prompt
expect {
    -re {\[.*\] >} {
        # Command completed, output is in expect_out(buffer)
        # The prompt will be included, so we're done
    }
    timeout {
        puts "ERROR: Timeout waiting for command completion"
        exit 1
    }
}

# Exit the session
send "exit\r"
expect eof
