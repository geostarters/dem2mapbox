# dem2mapbox
Python scripts to convert a GeoTIFF DEM file to the mapbox terrain RGB format

# How to use it
Use the ```mapboxTerrainMonothread.py``` script to run the encoder in a single thread or the ```mapboxTerrainMultithread.py``` script to run the encoder in multiple threads.

The first argument is a **_tif-encoded_ DEM file** and the second one the name of the output file.

## Changing the number of threads used
In order to change the number of threads used by the multithreaded version you can edit the script and change the ``threadedCols`` and ``threadedRows`` variables. The script will get the image and divide it by ``threadedCols*threadedRows`` tiles and assign a thread to each one of them.

## Examples
`python mapboxTerrainMultithread.py ./DEM.tif ./Mapbox.png`

`python mapboxTerrainMonothread.py ./DEM.tif ./Mapbox.png`


