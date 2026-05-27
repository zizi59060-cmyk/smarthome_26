from glob import glob
import os

from setuptools import setup


package_name = "robot_serial_comm"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="smarthome team",
    maintainer_email="you@example.com",
    description="Serial communication bridge for the smart-home vision/gimbal protocol.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "serial_comm_node = robot_serial_comm.serial_comm_node:main",
        ],
    },
)
