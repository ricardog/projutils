from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="projutils",
    version="0.1",
    author="Ricardo E. Gonzalez",
    author_email="ricardog@itinerisinc.com",
    description="Utilities for generating and visualizing raster maps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    url="https://github.com/ricardog/projutils",
    project_urls={
        "Bug Tracker": "https://github.com/ricardog/projutils/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "cartopy",
        "Click",
        "gdal",
        "fiona",
        "geopandas",
        "geopy",
        "joblib",
        "matplotlib",
        "netCDF4",
        "numpy",
        "pandas",
        "pylru",
        "r2py @ git+https://github.com/ricardog/r2py",
        "rasterset @ git+https://github.com/ricardog/rasterset",
        "rasterio",
        "scipy",
        "setuptools",
        "shapely",
        "tqdm",
        "xlrd",
    ],
    entry_points="""
        [console_scripts]
        extract_values=projutils.scripts.extract_values:main
        gen_hyde=projutils.scripts.gen_hyde:main
        gen_sps=projutils.scripts.gen_sps:main
        hyde2nc=projutils.scripts.hyde2nc:main
        nc_dump=projutils.scripts.nc_dump:main

        nctomp4=projutils.scripts.nctomp4:main
        project=projutils.scripts.project:cli
        rview=projutils.scripts.rview:main
        tifftomp4=projutils.scripts.tifftomp4:main
        tiffcmp=projutils.scripts.tiffcmp:main
    """,
)
