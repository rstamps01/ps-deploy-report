# 🔐 VAST API Token Authentication Guide

## Overview

The VAST As-Built Report Generator now supports API token authentication as an alternative to username/password authentication. This provides enhanced security and convenience for automated deployments and CI/CD pipelines.

## 🎯 Benefits

- **Enhanced Security**: Tokens can be scoped and have expiration dates
- **Automation Friendly**: No need to store passwords in scripts
- **Token Management**: Respects VAST's 5-token limit per user
- **Fallback Support**: Falls back to username/password if token fails
- **Environment Variables**: Support for `VAST_TOKEN` environment variable

## 🚀 Usage

### Command Line Usage

#### Using API Token (Recommended)
```bash
# Direct token specification
python main.py --cluster 10.143.11.204 --token YOUR_API_TOKEN --output ./reports

# Using environment variable
export VAST_TOKEN=YOUR_API_TOKEN
python main.py --cluster 10.143.11.204 --output ./reports
```

#### Using Username/Password (Fallback)
```bash
# Direct credentials
python main.py --cluster 10.143.11.204 --username admin --password 123456 --output ./reports

# Using environment variables
export VAST_USERNAME=admin
export VAST_PASSWORD=123456
python main.py --cluster 10.143.11.204 --output ./reports
```

#### Interactive Mode
```bash
# Will prompt for authentication method
python main.py --cluster 10.143.11.204 --output ./reports
```

### Programmatic Usage

```python
from api_handler import create_vast_api_handler

# Using API token
api_handler = create_vast_api_handler(
    cluster_ip="10.143.11.204",
    token="YOUR_API_TOKEN"
)

# Using username/password
api_handler = create_vast_api_handler(
    cluster_ip="10.143.11.204",
    username="admin",
    password="123456"
)

# Authenticate
if api_handler.authenticate():
    # Use the API handler
    cluster_data = api_handler.get_cluster_info()
```

## 🔄 Authentication Priority

The authentication system follows this priority order:

1. **API Token** (Highest Priority)
   - Command-line `--token` argument
   - `VAST_TOKEN` environment variable
   - Interactive token input

2. **Username/Password** (Fallback)
   - Command-line `--username` and `--password` arguments
   - `VAST_USERNAME` and `VAST_PASSWORD` environment variables
   - Interactive username/password input

3. **Existing Tokens** (Auto-discovery)
   - Checks for existing valid tokens on the cluster
   - Uses the first valid token found

4. **Token Creation** (Last Resort)
   - Creates new token if slots available (max 5 per user)
   - Respects token limit and provides clear error messages

## 🧪 Testing

### Test Token Authentication
```bash
# Test with your token
python test_token_auth.py 10.143.11.204 YOUR_API_TOKEN

# Test both token and username/password
python test_token_auth.py 10.143.11.204 YOUR_API_TOKEN admin 123456
```

### Test Report Generation
```bash
# Generate report with token
python main.py --cluster 10.143.11.204 --token YOUR_API_TOKEN --output ./reports --verbose

# Generate report with username/password
python main.py --cluster 10.143.11.204 --username admin --password 123456 --output ./reports --verbose
```

## 🔧 Configuration

### Environment Variables

```bash
# Token authentication
export VAST_TOKEN=your_api_token_here

# Username/password authentication
export VAST_USERNAME=admin
export VAST_PASSWORD=your_password_here

# Optional: Disable SSL verification (not recommended for production)
export VAST_VERIFY_SSL=false
```

### Configuration File

```yaml
# config/config.yaml
api:
  timeout: 30
  max_retries: 3
  verify_ssl: true

logging:
  level: INFO
  file: logs/vast_report_generator.log
```

## 🛡️ Security Best Practices

### Token Management
- **Rotate Tokens**: Regularly rotate API tokens
- **Scope Tokens**: Use tokens with minimal required permissions
- **Monitor Usage**: Check token usage in VAST web interface
- **Revoke Unused**: Remove unused tokens to free up slots

### Environment Variables
- **Secure Storage**: Store tokens in secure environment variable systems
- **No Hardcoding**: Never hardcode tokens in scripts
- **Access Control**: Limit access to environment variables
- **Audit Logs**: Monitor token usage and access

### Network Security
- **HTTPS Only**: Always use HTTPS for API communication
- **Certificate Validation**: Verify SSL certificates in production
- **Network Isolation**: Use VPN or private networks when possible

## 🚨 Troubleshooting

### Common Issues

#### Token Invalid or Expired
```
❌ Provided API token is invalid or expired
```
**Solution**: Generate a new token in the VAST web interface

#### Token Limit Reached
```
❌ Token limit reached (5 tokens max per user)
```
**Solution**: Revoke unused tokens or use username/password authentication

#### Authentication Failed
```
❌ All authentication methods failed
```
**Solution**:
1. Verify cluster IP address
2. Check network connectivity
3. Verify credentials/token
4. Check VAST cluster status

#### SSL Certificate Issues
```
❌ SSL: CERTIFICATE_VERIFY_FAILED
```
**Solution**:
1. Install proper certificates
2. Use `--insecure` flag (development only)
3. Set `VAST_VERIFY_SSL=false`

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python main.py --cluster 10.143.11.204 --token YOUR_TOKEN --output ./reports --verbose
```

## 📋 Migration Guide

### From Username/Password to Token

1. **Generate Token**: Create API token in VAST web interface
2. **Update Scripts**: Replace username/password with token
3. **Test Authentication**: Verify token works
4. **Update Environment**: Set `VAST_TOKEN` environment variable
5. **Remove Old Credentials**: Clean up username/password references

### Example Migration

**Before:**
```bash
export VAST_USERNAME=admin
export VAST_PASSWORD=password
python main.py --cluster 10.143.11.204 --output ./reports
```

**After:**
```bash
export VAST_TOKEN=your_api_token_here
python main.py --cluster 10.143.11.204 --output ./reports
```

## 🎉 Success Examples

### Successful Token Authentication
```
🔐 TESTING VAST API TOKEN AUTHENTICATION
==================================================
Cluster: 10.143.11.204
Token: abc1234567...xyz9

✅ API handler created with token
🔍 Testing authentication...
✅ Authentication successful!
🔍 Testing API calls...
✅ Cluster info retrieved: selab-var-204
✅ VMs data retrieved: 1 VMs found
✅ CNodes data retrieved: 3 CNodes found
✅ DNodes data retrieved: 2 DNodes found

🎉 TOKEN AUTHENTICATION TEST COMPLETED SUCCESSFULLY!
```

### Successful Report Generation
```
🎯 VAST AS-BUILT REPORT GENERATOR - EXECUTION SUMMARY
======================================================================
Cluster Name: selab-var-204
Cluster Version: release-5.3.1-sp3-1898015
Cluster State: ONLINE
PSNT: selab-var-204
Total Nodes: 5
CNodes: 3
DNodes: 2
Rack Positions Available: True
Overall Data Completeness: 95.2%
Enhanced Features Enabled: True

Output Directory: ./reports
JSON Report: Generated successfully
PDF Report: Generated successfully

======================================================================
REPORT GENERATION COMPLETED SUCCESSFULLY
======================================================================
```

## 📚 Additional Resources

- [VAST API Documentation](https://docs.vastdata.com/)
- [VAST Brand Guidelines](https://brand.vastdata.com/)
- [Report Generator Documentation](./README.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

**The VAST As-Built Report Generator now supports secure, token-based authentication for enhanced automation and security!** 🎉
