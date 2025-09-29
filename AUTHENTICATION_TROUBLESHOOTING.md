# VAST Authentication Troubleshooting Guide

## 🚨 Issue Identified

The error you're seeing:
```bash
jq: error (at <stdin>:0): Cannot index string with string "state"
```

**Root Cause**: The API is returning `{"detail":"Invalid username/password."}` instead of JSON data, which causes jq to fail when trying to parse it as JSON.

## 🔍 Diagnosis Results

✅ **Connection**: Successful to `10.143.11.204:443`  
✅ **SSL Certificate**: Valid (CN=*.selab.vastdata.com)  
❌ **Authentication**: Failed with "Invalid username/password"  
❌ **API Access**: No working API versions found  

## 🛠️ Solutions

### **Solution 1: Verify Credentials**

1. **Check the VAST Web Interface**:
   ```bash
   # Open in browser
   https://10.143.11.204
   ```
   - Try logging in with `admin` / `password`
   - If login fails, the credentials are incorrect

2. **Try Different Usernames**:
   - `admin`
   - `root` 
   - `vast`
   - `administrator`
   - Your actual username

3. **Try Different Passwords**:
   - `password`
   - `admin`
   - `vast`
   - `123456`
   - Your actual password

### **Solution 2: Use API Token Authentication**

If you have an API token, use it instead:

```bash
# Test with API token
curl -k -H "Authorization: Api-Token YOUR_TOKEN_HERE" "https://10.143.11.204/api/v7/clusters/"

# If successful, use this format for all commands:
curl -k -H "Authorization: Api-Token YOUR_TOKEN_HERE" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.id, .name, .mgmt_vip] | @csv'
```

### **Solution 3: Check Cluster Status**

1. **Verify Cluster is Running**:
   ```bash
   # Check if the cluster responds
   curl -k "https://10.143.11.204/api/v7/health/"
   ```

2. **Check Network Connectivity**:
   ```bash
   # Test basic connectivity
   ping 10.143.11.204
   telnet 10.143.11.204 443
   ```

### **Solution 4: Use Correct API Version**

Some clusters may use different API versions:

```bash
# Test different versions
curl -k -u "admin:password" "https://10.143.11.204/api/v1/clusters/"
curl -k -u "admin:password" "https://10.143.11.204/api/v2/clusters/"
curl -k -u "admin:password" "https://10.143.11.204/api/v3/clusters/"
```

## 🔧 Fixed Curl Commands

Once you have the correct credentials, use these **fixed commands** that handle authentication errors:

### **Basic Cluster Information**
```bash
curl -k -u "admin:CORRECT_PASSWORD" "https://10.143.11.204/api/v7/clusters/" | jq -r 'if type == "array" then .[] | [.id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time] | @csv else "Error: " + .detail end'
```

### **Cluster State Information**
```bash
curl -k -u "admin:CORRECT_PASSWORD" "https://10.143.11.204/api/v7/clusters/" | jq -r 'if type == "array" then .[] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv else "Error: " + .detail end'
```

### **All Commands with Error Handling**

Use the `fixed_curl_commands.py` script:

```bash
python3 fixed_curl_commands.py 10.143.11.204 admin CORRECT_PASSWORD
```

## 🧪 Testing Scripts

### **1. Test Authentication**
```bash
python3 test_auth.py 10.143.11.204 admin password
```

### **2. Test with Different Credentials**
```bash
python3 test_auth.py 10.143.11.204 admin admin
python3 test_auth.py 10.143.11.204 root password
python3 test_auth.py 10.143.11.204 vast vast
```

### **3. Test with API Token**
```bash
# If you have an API token
curl -k -H "Authorization: Api-Token YOUR_TOKEN" "https://10.143.11.204/api/v7/clusters/"
```

## 📋 Next Steps

1. **Get Correct Credentials**:
   - Check with your VAST administrator
   - Try the VAST web interface
   - Look for documentation or setup notes

2. **Test Authentication**:
   ```bash
   python3 test_auth.py 10.143.11.204 USERNAME PASSWORD
   ```

3. **Use Fixed Commands**:
   ```bash
   python3 fixed_curl_commands.py 10.143.11.204 USERNAME PASSWORD
   ```

4. **Import into Excel**:
   - Once authentication works, the commands will return proper CSV data
   - Copy the output and paste into Excel
   - Use "Text to Columns" with comma delimiter

## 🎯 Expected Results

Once authentication is fixed, you should see:

```bash
# Successful response
1,selab-var-204,10.143.11.204,https://10.143.11.204/api/v7/clusters/1,release-5.3.1-sp3-1898015,selab-var-204,127db70c-0197-5f4f-8af8-44bead61cda2,10 days 9:39:18.164634,2025-09-17T22:34:29.502591Z,2025-08-07T18:57:44.259621Z
```

Instead of:
```bash
# Error response
Error: Invalid username/password.
```

## 💡 Common Issues

1. **Wrong Password**: Most common issue
2. **Wrong Username**: Try different usernames
3. **API Token Required**: Some clusters require API tokens
4. **Network Issues**: Firewall or connectivity problems
5. **Cluster Down**: VAST cluster not running
6. **Wrong API Version**: Try different API versions

The key is to get the authentication working first, then the curl commands will return proper JSON data that jq can parse correctly.
