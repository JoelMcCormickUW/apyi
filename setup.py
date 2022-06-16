from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name ='apyi',
    version = '1.2.3',
    author = 'Joel McCormick',
    author_email = 'joe.lp.mccormick@gmail.com',
    description = 'TODO: write a description',
    long_description = long_description,
    url = 'https://github.com/JoelMcCormickUW/apyi',
    packages = find_packages(),
    install_requires = [
        'requests',
    ]
)

