from setuptools import setup
from glob import glob
import os

package_name = 'smarthome_task_manager'

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
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='smarthome team',
    maintainer_email='you@example.com',
    description='Mission state machine for smart-home sorting robot.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mission_node = smarthome_task_manager.mission_node:main',
        ],
    },
)
