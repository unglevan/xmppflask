"""
XmppFlask
---------

XmppFlask is a prototype of a microframework that mimics
`Flask <http://flask.pocoo.org>`_ web framework.

"""
from setuptools import setup, find_packages

setup(
    name='XmppFlask',
    version='0.0.1',
    url='http://xmppflask.org',
    license='BSD',
    author='Kostyantyn Rybnikov',
    author_email='k.bx@ya.ru',
    description='A XMPP microframework inspired by Flask',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'jinja2'
    ],
    entry_points={
        'console_scripts': [
            'xmppflask = xmppflask.run:main'
        ]
    },
    extras_require={
        'sleekxmpp': ["sleekxmpp>=1.1.2"],
        'xmpppy': ["xmpppy>=0.5.0rc1"],
        'redis': ['redis>=2.4'],
        'tests': ['mock', 'unittest2'],
        'dev': ['sleekxmpp', 'xmpppy', 'mock', 'nose', 'coverage']
    }
)
