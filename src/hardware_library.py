"""
Consolidated Hardware Library for VAST As-Built Reporter.

This module provides a single source of truth for all hardware device definitions,
including CBoxes, DBoxes, EBoxes, and Switches. All other modules should import
from here rather than maintaining their own device lists.

Usage:
    from hardware_library import BUILTIN_DEVICES, get_device_height, get_device_image
"""

from pathlib import Path
from typing import Any, Dict, Optional

# All built-in hardware devices with their properties
# Keys are lowercase model identifiers used for matching
BUILTIN_DEVICES: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # CBoxes (Compute Boxes)
    # =========================================================================
    "supermicro_gen5_cbox": {
        "type": "cbox",
        "height_u": 1,
        "image_filename": "supermicro_gen5_cbox_1u.png",
        "description": "Supermicro Gen5 CBox",
    },
    "hpe_genoa_cbox": {
        "type": "cbox",
        "height_u": 1,
        "image_filename": "hpe_genoa_cbox.png",
        "description": "HPE Genoa CBox",
    },
    "hpe_icelake": {
        "type": "cbox",
        "height_u": 2,
        "image_filename": "hpe_il_cbox_2u.png",
        "description": "HPE IceLake 2U CBox",
    },
    "dell_icelake": {
        "type": "cbox",
        "height_u": 2,
        "image_filename": "dell_il_cbox_2u.png",
        "description": "Dell IceLake 2U CBox",
    },
    "dell_turin_cbox": {
        "type": "cbox",
        "height_u": 1,
        "image_filename": "dell_turin_r6715_cbox_1u.png",
        "description": "Dell Gen6 Turin CBox (R6715)",
    },
    "supermicro_turin_cbox": {
        "type": "cbox",
        "height_u": 1,
        "image_filename": "smc_turin_cbox_1u.png",
        "description": "SMC Gen6 Turin CBox",
    },
    "smc_turin_cbox": {
        "type": "cbox",
        "height_u": 1,
        "image_filename": "smc_turin_cbox_1u.png",
        "description": "SMC Gen6 Turin CBox",
    },
    "broadwell": {
        "type": "cbox",
        "height_u": 2,
        "image_filename": "broadwell_cbox_2u.png",
        "description": "Broadwell 2U CBox",
    },
    "cascadelake": {
        "type": "cbox",
        "height_u": 2,
        "image_filename": "cascadelake_cbox_2u.png",
        "description": "CascadeLake 2U CBox",
    },
    # =========================================================================
    # DBoxes (Data Boxes)
    # =========================================================================
    "bluefield": {
        "type": "dbox",
        "height_u": 1,
        "image_filename": "ceres_v2_1u.png",
        "description": "Ceres V1 1U DBox",
    },
    "ceres_v2": {
        "type": "dbox",
        "height_u": 1,
        "image_filename": "ceres_v2_1u.png",
        "description": "Ceres V2 1U DBox",
    },
    "dbox-515": {
        "type": "dbox",
        "height_u": 1,
        "image_filename": "ceres_v2_1u.png",
        "description": "Ceres V2 1U DBox",
    },
    "dbox-516": {
        "type": "dbox",
        "height_u": 1,
        "image_filename": "ceres_v2_1u.png",
        "description": "Ceres V2 1U DBox",
    },
    "sanmina": {
        "type": "dbox",
        "height_u": 2,
        "image_filename": "maverick_2u.png",
        "description": "Maverick 2U DBox",
    },
    "maverick_1.5": {
        "type": "dbox",
        "height_u": 2,
        "image_filename": "maverick_2u.png",
        "description": "Maverick/MLK 2U DBox",
    },
    "ceres_4u": {
        "type": "dbox",
        "height_u": 2,
        "image_filename": None,  # Uses generic_2u.png fallback
        "description": "Ceres 4U 2U DBox",
    },
    # =========================================================================
    # EBoxes (Enclosure Boxes)
    # =========================================================================
    "supermicro_gen5_ebox": {
        "type": "ebox",
        "height_u": 1,
        "image_filename": "supermicro_gen5_ebox_1u.png",
        "description": "Supermicro Gen 5 EBox",
    },
    "dell_genoa_ebox": {
        "type": "ebox",
        "height_u": 1,
        "image_filename": "dell_genoa_ebox_1u.png",
        "description": "Dell Genoa 1U EBox",
    },
    # =========================================================================
    # Switches
    # =========================================================================
    "msn2100-cb2f": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "mellanox_msn2100_2x16p_100g_switch_1u.png",
        "description": "Mellanox SN2100 100Gb 16pt Switch",
    },
    "msn2700": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "mellanox_msn2700_1x32p_100g_switch_1u.png",
        "description": "Mellanox SN2700 100Gb 32pt Switch",
    },
    "msn3700-vs2fc": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "mellanox_msn3700_1x32p_200g_switch_1u.png",
        "description": "Mellanox SN3700 200Gb 32pt Switch",
    },
    "msn4600c": {
        "type": "switch",
        "height_u": 2,
        "image_filename": "mellanox_msn4600C_1x64p_100g_switch_2u.png",
        "description": "Mellanox SN4600C 100Gb 64pt Switch",
    },
    "msn4600": {
        "type": "switch",
        "height_u": 2,
        "image_filename": "mellanox_msn4600_1x64p_200g_switch_2u.png",
        "description": "Mellanox SN4600 200Gb 64pt Switch",
    },
    "msn4700-ws2rc": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "msn4700-ws2rc_1u.png",
        "description": "Mellanox SN4700 400Gb 32pt Switch",
    },
    "msn4700": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "msn4700-ws2rc_1u.png",
        "description": "Mellanox SN4700 400Gb 32pt Switch",
    },
    "sn5600": {
        "type": "switch",
        "height_u": 2,
        "image_filename": "mellanox_sn5600_1x64p_800g_switch_2u.png",
        "description": "Mellanox SN5600 800Gb 64pt Switch",
    },
    "arista_7050cx4": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "arista_7050cx4_24d_400g_switch_1u.png",
        "description": "Arista 7050CX4 400Gb Switch",
    },
    "arista_7050dx4": {
        "type": "switch",
        "height_u": 1,
        "image_filename": "arista_7050dx4_32s_400g_switch_1u.png",
        "description": "Arista 7050DX4 400Gb Switch",
    },
    "arista_7060dx5": {
        "type": "switch",
        "height_u": 2,
        "image_filename": "arista_7060dx5_1x64p_800g_switch_2u.jpeg",
        "description": "Arista 7060DX5 800Gb Switch",
    },
    "arista": {
        "type": "switch",
        "height_u": 2,
        "image_filename": "arista_7060dx5_1x64p_800g_switch_2u.jpeg",
        "description": "Arista Switch (generic)",
    },
    "n42c-00rb-7c0": {
        "type": "switch",
        "height_u": 2,
        "image_filename": "mellanox_sn5400_1x64p_400g_switch_2u.png",
        "description": "Mellanox SN5400 400Gb 64pt Switch",
    },
}


def get_builtin_devices_for_ui() -> Dict[str, Dict[str, Any]]:
    """
    Get built-in devices formatted for the Library UI.
    Adds 'source': 'built-in' to each entry.
    """
    return {key: {**value, "source": "built-in"} for key, value in BUILTIN_DEVICES.items()}


def get_device_height(model: str, user_library: Optional[Dict[str, Any]] = None) -> int:
    """
    Get the U-height for a device model.

    Args:
        model: Device model string (case-insensitive matching)
        user_library: Optional user-defined library to check after built-in

    Returns:
        Height in rack units (defaults to 1 if unknown)
    """
    if not model:
        return 1

    model_lower = model.lower()

    # EBox/enclosure default to 1U
    if "ebox" in model_lower or "enclosure" in model_lower:
        return 1

    # Check built-in devices (longest match first)
    for key in sorted(BUILTIN_DEVICES, key=len, reverse=True):
        if key in model_lower:
            return int(BUILTIN_DEVICES[key].get("height_u", 1))

    # Check user library
    if user_library:
        for key in sorted(user_library, key=len, reverse=True):
            if key in model_lower:
                return int(user_library[key].get("height_u", 1))

    return 1


def get_device_image_filename(model: str, user_library: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Get the image filename for a device model.

    Args:
        model: Device model string (case-insensitive matching)
        user_library: Optional user-defined library to check after built-in

    Returns:
        Image filename or None if not found
    """
    if not model:
        return None

    model_lower = model.lower()

    # Check built-in devices (longest match first)
    for key in sorted(BUILTIN_DEVICES, key=len, reverse=True):
        if key in model_lower:
            filename = BUILTIN_DEVICES[key].get("image_filename")
            return str(filename) if filename else None

    # Check user library
    if user_library:
        for key in sorted(user_library, key=len, reverse=True):
            if key in model_lower:
                filename = user_library[key].get("image_filename")
                return str(filename) if filename else None

    return None


def build_image_map(hardware_images_dir: Path) -> Dict[str, Path]:
    """
    Build a mapping of model keys to full image paths.

    Args:
        hardware_images_dir: Directory containing hardware images

    Returns:
        Dict mapping model keys to image file paths
    """
    image_map = {}
    for key, device in BUILTIN_DEVICES.items():
        filename = device.get("image_filename")
        if filename:
            image_map[key] = hardware_images_dir / filename
    return image_map
