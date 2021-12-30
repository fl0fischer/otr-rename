from setuptools import setup

setup(name='otr_rename',
      version='0.0.1',
      author='Florian Fischer',
      author_email='florian.fischer26@gmail.com',
      url='https://github.com/fl0fischer/otr-rename',
      license='LICENSE',
      description='This python script allows to easily rename movies and tv series episodes obtained from OnlineTVRecorder in batch mode.',
      long_description=open('README.md').read(),
      python_requires='>= 3.8',
      install_requires=['requests', 'beautifulsoup4', 'imdbpy']
)
