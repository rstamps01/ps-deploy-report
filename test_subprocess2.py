#!/usr/bin/env python3
import subprocess

print("Test 1: Using shell=True")
cmd_str = 'sshpass -p vastdata ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null vastdata@10.143.11.81 "clush -a hostname"'
result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=30)
print(f"Return code: {result.returncode}")
print(f"STDOUT:\n{result.stdout}")
print(f"STDERR:\n{result.stderr}\n")

print("\nTest 2: Adding SSHPASS env var")
import os
env = os.environ.copy()
env['SSHPASS'] = 'vastdata'
cmd = [
    "sshpass",
    "-e",  # Read password from SSHPASS env var
    "ssh",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "vastdata@10.143.11.81",
    "clush -a hostname",
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
print(f"Return code: {result.returncode}")
print(f"STDOUT:\n{result.stdout}")
print(f"STDERR:\n{result.stderr}")
