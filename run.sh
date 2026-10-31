#!/bin/bash

date
#python3 managedYoutubeDL update-channels config.yaml
#python3 managedYoutubeDL download-new config.yaml
python3 managedYoutubeDL download-new config.yaml --quality 1080p
#python3 managedYoutubeDL download-new config.yaml --quality max
#python3 managedYoutubeDL manual-download config.yaml $1
date
