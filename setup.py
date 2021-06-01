from setuptools import setup, find_packages

setup(
    name="projections",
    version="0.1",
    author="Ricardo E. Gonzalez",
    author_email="ricardog@itinerisinc.com",
    description="Spatio-temporal projections of R models using python",
    python_requires=">=3.8.3",
    url="https://github.com/NaturalHistoryMuseum/raster-project",
    project_urls={
        "Bug Tracker": "https://github.com/ricardog/raster-project/issues",
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
        extract_values=projections.scripts.extract_values:main
        gen_hyde=projections.scripts.gen_hyde:main
        gen_sps=projections.scripts.gen_sps:main
        hyde2nc=projections.scripts.hyde2nc:main
        nc_dump=projections.scripts.nc_dump:main

        nctomp4=projections.scripts.nctomp4:main
        project=projections.scripts.project:cli
        rview=projections.scripts.rview:main
        tifftomp4=projections.scripts.tifftomp4:main
        tiffcmp=projections.scripts.tiffcmp:main
    """,
)
