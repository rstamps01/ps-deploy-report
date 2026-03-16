#!/usr/bin/env python3
import subprocess

# Test exact command that works manually
cmd = [
    "sshpass",
    "-p",
    "vastdata",
    "ssh",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "vastdata@10.143.11.81",
    "clush -a hostname",
]

print("Command:", " ".join(cmd))
print("\nRunning via subprocess.run()...")

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

print(f"\nReturn code: {result.returncode}")
print(f"\nSTDOUT:\n{result.stdout}")
print(f"\nSTDERR:\n{result.stderr}")
