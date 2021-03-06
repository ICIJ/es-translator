import sys

from setuptools import setup, find_packages

py_version = sys.version_info[:2]
if py_version < (3, 6):
    raise Exception("es-translator requires Python >= 3.6.")

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='es-translator',
      version='1.2.0',
      packages=find_packages(),
      description="A lazy yet bulletproof machine translation tool for Elastichsearch.",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url="https://github.com/icij/es-translator",
      test_suite='nose.collector',
      tests_require=['nose', 'responses'],
      include_package_data=True,
      keywords=['datashare', 'api', 'text-mining', 'elasticsearch', 'apertium', 'translation'],
      classifiers=[
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU Affero General Public License v3",
          "Operating System :: OS Independent",
          "Topic :: Scientific/Engineering :: Information Analysis",
      ],
      install_requires=[
        'click==7.0',
        'elasticsearch<8.0.0,>=6.0.0',
        'elasticsearch-dsl<8.0.0,>=6.0.0',
        'sh==1.12.13',
        'pycountry==18.12.8',
        'deb-pkg-tools==5.2',
        'nose==1.3.7',
        'urllib3==1.25.10',
      ],
      python_requires='>=3.6',
      entry_points='''
        [console_scripts]
        es-translator=es_translator.cli:translate
        es-translator-pairs=es_translator.cli:pairs
    ''')
