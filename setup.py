from setuptools import setup, find_packages

setup(
    name="FloatingArk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'copernicusmarine',
        'xarray',
        'pandas',
        'numpy',
        'scikit-learn',
        'tensorflow',
        'matplotlib',
        'seaborn',
        'folium',
        'flask',
        'selenium',
        'scipy'
    ],
    author="Johan Sneider Espitia Peñuela",
    description="Sistema flotante elástico para generación de energía de olas en Colombia",
)