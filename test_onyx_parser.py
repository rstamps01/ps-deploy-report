#!/usr/bin/env python3
"""
Test script to manually capture and parse Onyx MAC table output
"""

import subprocess
import re

# Test with actual Onyx switch
switch_ip = "10.27.16.173"
username = "admin"
password = "admin"

print("=" * 80)
print("Testing Onyx MAC Table Collection and Parsing")
print("=" * 80)

# Test 1: Capture raw output using pexpect
print("\n📝 Test 1: Capturing raw output with pexpect...")
try:
    import pexpect

    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {username}@{switch_ip}"
    child = pexpect.spawn(ssh_cmd, timeout=30, encoding="utf-8")

    # Wait for password
    child.expect([r"Password:", r"password:"])
    child.sendline(password)

    # Wait for prompt
    child.expect([r"\[.*\]\s*>"])

    # Send command - TEST GENERAL TABLE (not VLAN-specific)
    child.sendline("show mac-address-table")

    # Wait for next prompt
    child.expect([r"\[.*\]\s*>"])

    # Get output
    raw_output = child.before

    # Exit
    child.sendline("exit")
    child.expect(pexpect.EOF)
    child.close()

    print(f"✅ Captured {len(raw_output)} characters")
    print(f"✅ Number of lines: {len(raw_output.split(chr(10)))}")

    # Save to file for inspection
    with open("test_onyx_raw_output.txt", "w") as f:
        f.write(raw_output)
    print("✅ Saved to: test_onyx_raw_output.txt")

    # Clean up output (remove first line with echoed command)
    lines = raw_output.split("\n")
    if lines and "show mac-address-table" in lines[0]:
        lines = lines[1:]
    cleaned_output = "\n".join(lines).strip()

    print(f"\n📄 First 500 chars of cleaned output:")
    print("-" * 80)
    print(cleaned_output[:500])
    print("-" * 80)

    # Test 2: Parse the output
    print("\n🔍 Test 2: Parsing MAC addresses...")

    mac_table = {}
    pattern = r"(\d+)\s+([0-9A-Fa-f:]+)\s+\w+\s+(\S+)"

    for line in cleaned_output.split("\n"):
        line = line.strip()
        if not line or line.startswith("-") or "Vlan" in line:
            continue

        match = re.search(pattern, line)
        if match:
            vlan = match.group(1)
            mac = match.group(2).lower()
            port = match.group(3)

            # Convert Eth1/X to swpX for consistency
            if port.startswith("Eth1/"):
                port_num = port.split("/")[-1]
                port = f"swp{port_num}"

            mac_table[mac] = {"port": port, "vlan": vlan}
            print(f"  ✅ Found: VLAN {vlan}, MAC {mac}, Port {port}")
        else:
            if len(line) > 10:  # Only show non-empty lines
                print(f"  ❌ No match: {line[:60]}")

    print(f"\n✅ Total MACs parsed: {len(mac_table)}")

except ImportError:
    print("❌ pexpect not installed. Run: pip3 install pexpect")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
