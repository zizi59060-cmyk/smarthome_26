from setuptools import setup
from glob import glob
import os

package_name = 'smarthome_comm'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='smarthome team',
    maintainer_email='you@example.com',
    description='Unified upper-lower computer communication package.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'comm_node = smarthome_comm.comm_node:main',
            'vision_pose_adapter = smarthome_comm.vision_pose_adapter:main',
        ],
    },
)
