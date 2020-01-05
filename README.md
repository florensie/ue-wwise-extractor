# Unreal Engine Wwise Extractor
This python script uses [WWise bnk Extractor](https://github.com/eXpl0it3r/bnkextr) and [vgmstream](https://github.com/losnoco/vgmstream) to extract and convert Wwise audio from Unreal Engine games.

## Compatibility
This script will only work on unreal games that don't package assets or on extracted .pak files (using quickbms or otherwise).
You'll have to find the directory containing the Wwise audio files (probably `Extracted Pak\GameName\Content\WwiseAudio\Windows`).
The directory should contain `.json` and `.bnk` files and optionally also `.wem` files.
If it doesn't, then this script won't work with the game.
The script was only tested with Satisfactory.

## Installation
This is a straightforward python script. You'll need a python installation of version 3.6 or greater.

## Usage
The Wwise directory should be passed to the script as it's only argument.

```python extract.py path/to/wwise/dir```

The extracted and converted audio files will show up under `out/[audio bank name]/`.