from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'rosmaster_webrtc'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'web'), glob('web/*')),
        (os.path.join('share', package_name, 'systemd'), glob('systemd/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'webrtc_bridge = rosmaster_webrtc.webrtc_bridge:main',
        ],
    },
)
