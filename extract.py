import sys
from pathlib import Path
import json
import subprocess
import os
import shutil

# Require python 3.8 or above
assert sys.version_info >= (3, 8)

# File paths
MODULE_PATH = Path(__file__).parent.absolute()
TMP_PATH = MODULE_PATH / Path('tmp')
OUT_PATH = MODULE_PATH / Path('out')
VGMSTREAM_EXE = MODULE_PATH / Path('test/test.exe') # Available at https://vgmstream.org
BNKTOOL_SCRIPT = MODULE_PATH / Path('bnktool.py') # Available at https://github.com/blueglyph/bnktool

DIV_LENGTH = 50

N_BANKS = 0
N_STREAMED = 0
N_MEMORY = 0
N_EVENTS = 0


def create_dir(path):
    """Helper method to create a directory if it doesn't exist yet"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        print(f'Cannot create directory ({path}) because file with same name exists')
        sys.exit(1)


def cleanup():
    """Cleanup the out and tmp directories"""
    if TMP_PATH.exists():
        shutil.rmtree(TMP_PATH)
    if OUT_PATH.exists():
        shutil.rmtree(OUT_PATH)

    create_dir(TMP_PATH)
    create_dir(OUT_PATH)


def convert_wem(input_path, output_path):
    subprocess.run([
        VGMSTREAM_EXE,  # Executable
        #'-l', '2', # Loop each track twice
        #'-f', '10', # Fade out 10 seconds before track end
        '-o', output_path,  # Output path
        input_path  # Input path
    ], capture_output=True, encoding='utf-8')


def process_object(soundbank, wwise_path, bank_out_path):
    global N_BANKS, N_STREAMED, N_MEMORY, N_EVENTS

    if 'IncludedEvents' in soundbank:
        for event in soundbank['IncludedEvents']:
            process_object(event, wwise_path, bank_out_path)
            N_EVENTS += 1

    if 'ReferencedStreamedFiles' in soundbank:
        for file in soundbank['ReferencedStreamedFiles']:
            source = wwise_path / (file['Id'] + '.wem')
            dest = bank_out_path / file['ShortName']

            # ShortName might contain more subdirectories, make sure they exist
            create_dir(dest.parent)

            print(f'output: {file["ShortName"]}')
            convert_wem(source, dest)
            N_STREAMED += 1

    if 'IncludedMemoryFiles' in soundbank:
        for file in soundbank['IncludedMemoryFiles']:
            # Prefetched files are actually in ReferencedStreamedFiles and should thus be skipped
            if 'PrefetchSize' not in file:
                source = TMP_PATH / Path(f'{file["Id"]}.wem')
                dest = bank_out_path / file['ShortName']

                # ShortName might contain more subdirectories, make sure they exist
                create_dir(dest.parent)

                print(f'output: {file["ShortName"]}')
                convert_wem(source, dest)
                N_MEMORY += 1


def main(argv):
    global N_BANKS

    # Argument validation
    err = False
    if len(argv) == 0:
        print('Missing argument')
        err = True
    elif len(argv) > 1:
        print('Too many arguments')
        err = True
    else:
        wwise_path = Path(argv[0]).absolute()
        if not wwise_path.exists():
            print('Invalid pak directory')
            err = True
    if err:
        print('extract.py <path to pak wwise directory>')
        sys.exit(2)

    cleanup()

    # noinspection PyUnboundLocalVariable
    # Note: identical xml soundbank meta files are also present but json files are easier to work with in py
    for json_path in list(wwise_path.glob('*.json')):  # Iterate over all json files in the directory
        print('=' * DIV_LENGTH)  # Divider

        # Make sure json file is a soundbank meta
        if json_path.name.lower() == 'soundbanksinfo.json':
            print(f'Non SoundBankInfo json file skipped: {json_path}')
            continue

        dict_ = json.loads(json_path.read_bytes())
        if ('SoundBanksInfo' not in dict_) or ('SoundBanks' not in dict_['SoundBanksInfo']):
            print(f'Non SoundBankInfo json file skipped: {json_path}')
            continue

        for soundbank in dict_['SoundBanksInfo']['SoundBanks']:
            print(f'Bank: {soundbank["ShortName"]} in {json_path.name}')

            bank_out_path = OUT_PATH.absolute() / soundbank['ShortName']
            if bank_out_path.exists():
                print('Duplicate bank?! Skipping.')
                continue

            create_dir(bank_out_path)
            N_BANKS += 1

            # Extract soundbank to cwd
            unpack_bnk = ('Path' in soundbank) and soundbank['Path'].endswith('.bnk')
            if unpack_bnk:
                create_dir(TMP_PATH)
                os.chdir(TMP_PATH)  # Go to tmp directory for bnkextr output
                subprocess.run(['python', BNKTOOL_SCRIPT, wwise_path / soundbank['Path'], '-x'], capture_output=True, encoding='utf-8')
                os.chdir(MODULE_PATH)

            # Process object
            process_object(soundbank, wwise_path, bank_out_path)

            # Delete unpacked bnk data
            if unpack_bnk: shutil.rmtree(TMP_PATH)

    print('=' * DIV_LENGTH)  # Divider

    print(f'Done. Converted {N_MEMORY + N_STREAMED} files ({N_STREAMED} disk, {N_MEMORY} mem, {N_EVENTS} event) from {N_BANKS} banks.')


if __name__ == '__main__':
    main(sys.argv[1:])
