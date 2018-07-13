from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()


setup(name='nexedge',
      version='0.2',
      description='Kenwood Nexedge communication',
      url='https://gitlab.com/evocount/nexedge',
      author='Suthep Pomjaksilp',
      author_email='sp@laz0r.de',
      license='proprietary',
      packages=['nexedge'],
      install_requires=[
          'pyserial-asyncio',
      ],

      zip_safe=False)
