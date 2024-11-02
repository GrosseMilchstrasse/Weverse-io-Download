import os
import requests
from urllib.parse import urlparse, parse_qs

def sanitize_filename(url):
    return url.split('/')[-1].split('?')[0]

def get_unique_filename(output_folder, filename):
    """
    Check if the filename exists in the output folder.
    If it does, add a unique number suffix to avoid overwriting.
    """
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    
    while os.path.exists(os.path.join(output_folder, unique_filename)):
        unique_filename = f"{base}_{counter}{extension}"
        counter += 1
    
    return unique_filename

def download_m3u8_file(m3u8_url, folder):
    os.makedirs(folder, exist_ok=True)
    m3u8_filename = sanitize_filename(m3u8_url)
    file_path = os.path.join(folder, m3u8_filename)
    
    try:
        response = requests.get(m3u8_url)
        response.raise_for_status()
        
        with open(file_path, 'wb') as file:
            file.write(response.content)
        
        print(f"Downloaded .m3u8 file to {file_path}")
        return file_path
    except Exception as e:
        print(f"Failed to download .m3u8 file: {e}")
        return None

def extract_ts_urls_from_m3u8(m3u8_file, base_url, ts_urls_txt, gda_param=""):
    ts_urls = []
    with open(m3u8_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                if gda_param:
                    line += f"{gda_param}"
                ts_urls.append(base_url + line)

    with open(ts_urls_txt, 'w') as f:
        for url in ts_urls:
            f.write(url + '\n')
    
    print(f"Extracted .ts URLs to {ts_urls_txt}")
    return ts_urls

def download_ts_files(ts_urls, folder):
    os.makedirs(folder, exist_ok=True)
    for url in ts_urls:
        try:
            filename = os.path.join(folder, sanitize_filename(url))
            print(f"Downloading {filename}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            print(f"Downloaded {filename} successfully.")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def create_ffmpeg_file_list(ts_urls, folder):
    list_file_path = os.path.join(folder, "file_list.txt")
    with open(list_file_path, 'w') as file:
        for url in ts_urls:
            ts_file = os.path.join(folder, sanitize_filename(url))
            file.write(f"file '{ts_file}'\n")
    print(f"Created FFmpeg file list at {list_file_path}")
    return list_file_path

def combine_ts_files_ffmpeg(file_list_path, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.system(f"ffmpeg -f concat -safe 0 -i \"{file_list_path}\" -c copy \"{output_file}\"")
    print(f"Combined .ts files into {output_file}")

def cleanup_ts_files(ts_folder):
    for ts_file in os.listdir(ts_folder):
        if ts_file.endswith('.ts'):
            os.remove(os.path.join(ts_folder, ts_file))
    print("All .ts files have been deleted.")

def get_base_url(m3u8_url):
    parsed_url = urlparse(m3u8_url)
    base_path = '/'.join(parsed_url.path.split('/')[:-1]) + '/'
    return parsed_url.scheme + '://' + parsed_url.netloc + base_path

def extract_gda_param(m3u8_url):
    parsed_url = urlparse(m3u8_url)
    gda_param = parse_qs(parsed_url.query).get("__gda__", [""])[0]
    return f"?__gda__={gda_param}" if gda_param else ""

if __name__ == "__main__":
    m3u8_url = input("Enter the .m3u8 URL: ").strip()
    output_file_name = input("Enter output file name (with extension, e.g., video.mp4): ").strip()

    # Set default file name if none is provided
    if not output_file_name:
        output_file_name = "combined_video.mp4"

    # Ensure the output filename is unique
    output_folder = "output_video"
    output_file_name = get_unique_filename(output_folder, output_file_name)

    base_url = get_base_url(m3u8_url)
    gda_param = extract_gda_param(m3u8_url)
    temp_folder = "temp_files"
    m3u8_file = download_m3u8_file(m3u8_url, temp_folder)

    if m3u8_file:
        ts_urls_txt = os.path.join(temp_folder, "ts_urls_list.txt")
        ts_urls = extract_ts_urls_from_m3u8(m3u8_file, base_url, ts_urls_txt, gda_param)

        if ts_urls:
            download_ts_files(ts_urls, temp_folder)
            
            ffmpeg_file_list = create_ffmpeg_file_list(ts_urls, temp_folder)
            
            output_video_file = os.path.join(output_folder, output_file_name)
            combine_ts_files_ffmpeg(ffmpeg_file_list, output_video_file)
            
            cleanup_ts_files(temp_folder)
