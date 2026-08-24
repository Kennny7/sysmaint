from setuptools import find_packages, setup

setup(
    name="sysmaint",
    version="2.0.0",
    description="Professional Cross-Platform System Maintenance & Optimization Suite",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "sysmaint=sysmaint.cli:main",
            "sysmaint-gui=sysmaint.gui.app:launch_gui",
        ],
    },
)
