from setuptools import setup

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='cbpi4-HA-Actor',
      version='0.0.1',
      description='CraftBeerPi4 Home Assistant Actor Plugin',
      author='Arco Veenhuizen',
      author_email='info@veenhuizen.net',
      url='https://github.com/arcidodo/cbpi4-HA-Actor',
      license='GPLv3',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
                  '': ['*.txt', '*.rst', '*.yaml'],
                  'cbpi4-HA-Actor': ['*', '*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-HA-Actor'],
      install_requires=[
            'cbpi4>=4.0.0.34',
      ],
      long_description=long_description,
      long_description_content_type='text/markdown'
      )
