"""
Vox - AI-powered text rewriting through macOS contextual menu

Setup script for building with py2app.
"""
from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "py2app": {
        "argv_emulation": False,
        "plist": {
            "CFBundleName": "Vox",
            "CFBundleDisplayName": "Vox",
            "CFBundleIdentifier": "com.voxapp.rewrite",
            "CFBundleVersion": "0.1.0",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": True,
            "NSServices": [
                {
                    "NSMessage": "vox.service",
                    "NSMenuItem": {"default": "Rewrite with Vox"},
                    "NSKeyEquivalent": {"default": ""},
                    "NSRestrictedContext": True,
                }
            ],
        },
        "includes": [
            "vox",
            "vox.service",
            "vox.api",
            "vox.config",
            "vox.ui",
            "vox.notifications",
        ],
        "packages": ["vox"],
    }
}

setup(
    name="Vox",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS["py2app"]},
    setup_requires=["py2app"],
)
