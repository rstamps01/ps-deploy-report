# Development Documentation

## Overview

This project contains internal development documentation that includes:
- Implementation guides
- Technical analysis documents
- Port mapping command references
- SSH configuration examples

## Security Note

⚠️ **These documents contain example credentials and passwords for development/testing purposes.**

For security reasons, these files are:
- **NOT tracked in git** (listed in `.gitignore`)
- **Kept local only** on developer machines
- **Never pushed to GitHub**

## Development Documentation Files

The following files exist locally but are excluded from version control:

1. **CLUSH_PTY_ISSUE_ANALYSIS.md**
   - Analysis of PTY allocation issues with clush
   - Contains example SSH commands with test credentials

2. **ONYX_SUPPORT_IMPLEMENTATION_COMPLETE.md**
   - Mellanox Onyx implementation summary
   - Contains test credentials and command examples

3. **MELLANOX_ONYX_PORT_MAPPING_COMMANDS.md**
   - Onyx CLI command reference
   - Contains default and test passwords

4. **MELLANOX_ONYX_ANALYSIS_MSN2100.md**
   - MSN2100 switch output analysis
   - Contains credential examples

5. **SSH_KEY_SETUP_REQUIRED.md**
   - SSH key authentication guide
   - Contains connection examples

6. **HARDWARE_IMAGE_IMPLEMENTATION_COMPLETE.md**
   - Hardware image mapping implementation
   - May contain environment-specific details

## For Developers

If you need access to these documents:
1. Contact the repository maintainer
2. Documents will be shared via secure channel
3. Keep them local only - never commit to git

## Best Practices

When creating development documentation:
- ✅ Use placeholder credentials (e.g., `<PASSWORD>`, `<USERNAME>`)
- ✅ Redact actual passwords before sharing
- ✅ Add sensitive files to `.gitignore`
- ❌ Never commit real credentials to git
- ❌ Never push development docs with passwords

## Credential Management

For actual deployment:
- Use environment variables
- Use secure credential management systems
- Use SSH key authentication where possible
- Rotate credentials regularly
