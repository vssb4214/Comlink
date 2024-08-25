import os
import shutil
import subprocess
import sys
import pkg_resources

required = {'grpcio', 'numpy', 'librosa', 'protobuf'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

if missing:
    print("Missing required modules. Installing...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])

REAL_FILES_DIR = '/Users/surajbendi/Desktop/tester/test-audio/real'
FAKE_FILES_DIR = '/Users/surajbendi/Desktop/tester/test-audio/fake'
SAMPLE_PATH = '/Users/surajbendi/Desktop/tester/test-audio/samples'
STATS_DIR = '/Users/surajbendi/Desktop/tester/test-audio/Stats'
DFQUERY_PATH = '/Users/surajbendi/Desktop/tester/dfquery.py'

def create_sample_folders_and_copy_files(src_dir, sample_path):
    for file in os.listdir(src_dir):
        if file.endswith('.wav'):
            folder_name = os.path.splitext(file)[0]
            folder_path = os.path.join(sample_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            src_file_path = os.path.join(src_dir, file)
            dest_file_path = os.path.join(folder_path, file)
            shutil.copy(src_file_path, dest_file_path)

def process_files_in_sample_folders(sample_path):
    for folder in os.listdir(sample_path):
        folder_path = os.path.join(sample_path, folder)
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith('.wav'):
                    audio_file = os.path.join(folder_path, file)
                    output_csv = os.path.join(folder_path, 'output.csv')
                    
                    cmd = ["/usr/bin/python3", DFQUERY_PATH, "-u", "IP", "-f", audio_file, "-o", "0", "-n", "1000", "-s", "-c"]
                    with open(output_csv, 'w') as f:
                        subprocess.run(cmd, stdout=f, check=True)
                    
                    stats_file = os.path.join(STATS_DIR, f'{folder}.csv')
                    os.makedirs(STATS_DIR, exist_ok=True)
                    shutil.copy(output_csv, stats_file)

def main():
    create_sample_folders_and_copy_files(REAL_FILES_DIR, SAMPLE_PATH)
    create_sample_folders_and_copy_files(FAKE_FILES_DIR, SAMPLE_PATH)
    
    process_files_in_sample_folders(SAMPLE_PATH)

if __name__ == "__main__":
    main()
