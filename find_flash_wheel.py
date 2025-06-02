import sys
import platform
import re
import subprocess
import os

def get_python_version_tag():
    major, minor, _ = platform.python_version_tuple()
    return f"cp{major}{minor}"

def get_torch_version_from_import():
    try:
        import torch
        version = torch.__version__
        # Normalize: 2.4.0+cu121 -> 2.4.0, also handles 2.1.0a0+git... -> 2.1.0
        base_version = version.split('+')[0]
        base_version = base_version.split('a0')[0] 
        return base_version
    except ImportError:
        print("Error: PyTorch is not installed or accessible in the current environment. Cannot determine PyTorch version for flash-attention.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error getting PyTorch version: {e}", file=sys.stderr)
        return None

def find_flash_attn_wheel(flash_txt_content, py_tag, cuda_tag, torch_ver):
    if not torch_ver:
        return None

    # Match major.minor of torch version (e.g., if torch_ver is "2.4.0", pattern becomes "torch2.4")
    torch_major_minor = '.'.join(torch_ver.split('.')[:2])
    torch_ver_search_pattern = f"torch{torch_major_minor}"
    
    print(f"Searching for flash-attention wheel: Python '{py_tag}', CUDA '{cuda_tag}', PyTorch base '{torch_ver}' (filename pattern '{torch_ver_search_pattern}')", file=sys.stderr)
    best_match_url = None    
    parsed_urls = []

    for url_line in flash_txt_content.strip().splitlines():
        url = url_line.strip()
        if not url: continue
        filename = url.split('/')[-1]
        
        # Extract flash_attn version (e.g., 2.7.0 or 2.7.0.post2)
        match_flash_ver = re.search(r"flash_attn-([\d\.]+(?:\.post\d+)?)", filename)
        if match_flash_ver:
            flash_ver_str = match_flash_ver.group(1)
            parts = []
            if ".post" in flash_ver_str:
                main_ver, post_val_str = flash_ver_str.split(".post")
                if not post_val_str.isdigit():
                    print(f"Warning: Non-numeric post-release tag '{post_val_str}' in '{flash_ver_str}' from filename '{filename}'. Skipping.", file=sys.stderr)
                    continue
                post_part = int(post_val_str)
                
                # Filter out empty strings from split and ensure there are numeric parts
                numeric_parts_str = [p for p in main_ver.split('.') if p]
                if not numeric_parts_str: # e.g. if main_ver was "" or ".."
                    print(f"Warning: Empty numeric part in version '{main_ver}' (from '{flash_ver_str}') in filename '{filename}'. Skipping.", file=sys.stderr)
                    continue
                try:
                    parts = [int(p) for p in numeric_parts_str] + [post_part]
                except ValueError:
                    print(f"Warning: Could not parse numeric parts from '{main_ver}' (from '{flash_ver_str}') in filename '{filename}'. Skipping.", file=sys.stderr)
                    continue
            else:
                # Filter out empty strings from split and ensure there are numeric parts
                numeric_parts_str = [p for p in flash_ver_str.split('.') if p]
                if not numeric_parts_str: # e.g. if flash_ver_str was "" or ".."
                    print(f"Warning: Empty numeric part in version '{flash_ver_str}' in filename '{filename}'. Skipping.", file=sys.stderr)
                    continue
                try:
                    parts = [int(p) for p in numeric_parts_str]
                except ValueError:
                    print(f"Warning: Could not parse numeric parts from '{flash_ver_str}' in filename '{filename}'. Skipping.", file=sys.stderr)
                    continue
            parsed_urls.append({"url": url, "filename": filename, "version_tuple": tuple(parts)})
            
    # Sort by flash_attn version (descending) to prefer newer versions
    parsed_urls.sort(key=lambda x: x["version_tuple"], reverse=True)

    for item in parsed_urls:
        filename = item["filename"]
        # Check for python tag, cuda tag, and torch version pattern in the filename
        if py_tag in filename and cuda_tag in filename and torch_ver_search_pattern in filename:
            print(f"Found compatible wheel: {item['url']}", file=sys.stderr)
            best_match_url = item['url']
            break # Found the best match
            
    if not best_match_url:
        print(f"No suitable flash-attention wheel found in flash.txt for Python {py_tag}, CUDA {cuda_tag}, PyTorch {torch_ver} (pattern {torch_ver_search_pattern})", file=sys.stderr)
    return best_match_url

def install_wheel_with_uv(wheel_url):
    if not wheel_url: return False
    try:
        print(f"Attempting to install flash-attention from: {wheel_url}", file=sys.stderr)
        command = ["uv", "pip", "install", wheel_url]
        process = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr)
        process.communicate() # Wait for completion
        if process.returncode == 0:
            print(f"Successfully installed {wheel_url}", file=sys.stderr)
            return True
        else:
            print(f"Failed to install {wheel_url}. 'uv pip install' exited with code: {process.returncode}", file=sys.stderr)
            return False
    except FileNotFoundError: # Should not happen if uv is used for other pip installs
        print("Error: 'uv' command not found. Make sure Pinokio's environment is set up correctly.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An error occurred during flash-attention installation: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3: # Script name, cuda_tag, flash_txt_path
        print("Usage: python find_flash_wheel.py <cuda_tag e.g. cu126|cu128> <path_to_flash_txt>", file=sys.stderr)
        sys.exit(1)
    target_cuda_tag = sys.argv[1]
    flash_txt_file_path = sys.argv[2]
    python_tag = get_python_version_tag()
    torch_version = get_torch_version_from_import()
    if not torch_version: sys.exit(1) # PyTorch not found or version undetectable
    try:
        with open(flash_txt_file_path, 'r') as f:
            flash_content = f.read()
    except FileNotFoundError:
        print(f"Error: flash.txt not found at {flash_txt_file_path}", file=sys.stderr)
        sys.exit(1)
    wheel_url_to_install = find_flash_attn_wheel(flash_content, python_tag, target_cuda_tag, torch_version)
    if wheel_url_to_install:
        if install_wheel_with_uv(wheel_url_to_install):
            sys.exit(0) # Successfully found and installed
        else:
            sys.exit(1) # Found but failed to install
    else:
        # No wheel found, exit gracefully. Main requirements.txt will handle flash-attn.
        sys.exit(0)