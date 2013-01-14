from setuptools import setup


setup(
    name='psi_cortex',
    packages=['micropsi_core', 'micropsi_server'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['PasteScript'],
    extras_require={
        "tests": ['pytest'],
    },
    entry_points="""
        [paste.app_factory]
        main = micropsi_server:main
    """,
)
