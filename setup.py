from setuptools import setup


extra = {}
with open('README', 'r') as f:
    extra['long_description'] = f.read()


setup(
    name='grenado',
    version='0.0.1',
    description="Greenlets for Tornado",
    url='https://github.com/KLab/grenado/',
    license='Apache 2.0',
    packages=['grenado'],
    install_requires=['greenlet'],
)
