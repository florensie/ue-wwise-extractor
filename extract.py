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
VGMSTREAM_EXE = MODULE_PATH / Path('test/test.exe')
BANK_EXTR_EXE = MODULE_PATH / Path('bnkextr.exe')

DIV_LENGTH = 50


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
        '-o', output_path,  # Output path
        input_path  # Input path
    ])


def main(argv):
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

    # Stats
    n_banks = 0
    n_streamed = 0
    n_memory = 0

    # noinspection PyUnboundLocalVariable
    # Note: identical xml soundbank meta files are also present but json files are easier to work with in py
    for json_path in list(wwise_path.glob('*.json')):  # Iterate over all json files in the directory
        dict_ = json.loads(json_path.read_bytes())
        if 'SoundBanksInfo' in dict_:  # Make sure json file is a soundbank meta
            for soundbank in dict_['SoundBanksInfo']['SoundBanks']:
                print(f'Bank: {soundbank["ShortName"]} in {json_path.name}')
                print('=' * DIV_LENGTH)

                bank_out_path = OUT_PATH.absolute() / soundbank['ShortName']
                if bank_out_path.exists():
                    print('Duplicate bank?! Skipping.')
                    continue
                create_dir(bank_out_path)
                n_banks += 1

                if 'ReferencedStreamedFiles' in soundbank:
                    for file in soundbank['ReferencedStreamedFiles']:
                        source = wwise_path / (file['Id'] + '.wem')
                        dest = bank_out_path / file['ShortName']

                        # ShortName might contain more subdirectories, make sure they exist
                        create_dir(dest.parent)

                        print(f'output: {file["ShortName"]}')
                        convert_wem(source, dest)
                        n_streamed += 1
                        print('-' * DIV_LENGTH)  # Divider

                if 'IncludedMemoryFiles' in soundbank:
                    os.chdir(TMP_PATH)  # Go to tmp directory for bnkextr output

                    i = 1
                    subprocess.run([BANK_EXTR_EXE, wwise_path / soundbank['Path']])  # Extract soundbank to cwd
                    for file in soundbank['IncludedMemoryFiles']:

                        # Prefetched files are actually in ReferencedStreamedFiles and should thus be skipped
                        if 'PrefetchSize' not in file:
                            source = Path(f'{i:04d}.wem')  # Filename for bnkextr output (4 digits, leading zeroes)
                            dest = bank_out_path / file['ShortName']

                            # ShortName might contain more subdirectories, make sure they exist
                            create_dir(dest.parent)

                            print(f'output: {file["ShortName"]}')
                            convert_wem(source, dest)
                            n_memory += 1
                            print('-' * DIV_LENGTH)  # Divider
                        i += 1

                    os.chdir(MODULE_PATH)

        else:
            print(f'Non SoundBankInfo json file skipped: {json_path}')

        print('=' * DIV_LENGTH)  # Divider

    print(f'Done. Converted {n_memory + n_streamed} files ({n_streamed} disk, {n_memory} mem) from {n_banks} banks.')


if __name__ == '__main__':
    main(sys.argv[1:])
