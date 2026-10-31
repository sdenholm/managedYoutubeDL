#!/bin/bash

date
#python3 managedYoutubeDL update-channels config.yaml
#python3 managedYoutubeDL download-new config.yaml
#python3 managedYoutubeDL manual-download config.yaml $1 --quality 1080p
python3 managedYoutubeDL manual-download config.yaml $1
#python3 managedYoutubeDL manual-download config.yaml $1 --quality $2
