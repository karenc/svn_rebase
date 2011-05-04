from setuptools import setup

version = '0.0.4'

setup(
    name='svn_rebase',
    version=version,
    description="Simple git rebase in SVN",
    url='http://github.com/karenc/svn_rebase',
    keywords="svn rebase git",
    author="Karen Chan",
    author_email="karen.chan@isotoma.com",
    license="Apache Software License",
    packages=['svn_rebase'],
    include_package_data=True,
    zip_safe=False,
#    install_requires=[ 
#        'setuptools',
#    ],  

    entry_points={
        'console_scripts': [
            'svn_rebase = svn_rebase:main',
            'svn_merge = svn_rebase:main',
            ]
    }
)
