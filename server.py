from flask import Flask, request, jsonify
from flask_cors import CORS
import zipfile
import os
import re
import shutil


app = Flask(__name__)
CORS(app)

def get_dimensions(zip_path):
    extract_folder = 'gerber_extracted'
    if os.path.exists(extract_folder):
        shutil.rmtree(extract_folder)
    os.makedirs(extract_folder)

    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_folder)

    outline_file = None
    for filename in os.listdir(extract_folder):
        if filename.upper().endswith('.GKO'):
            outline_file = os.path.join(extract_folder, filename)
            break

    if not outline_file:
        return None, None

    with open(outline_file, 'r') as f:
        content = f.read()

    fmt_match = re.search(r'%FSLA[TL]?X(\d)(\d)Y(\d)(\d)\*%', content)
    if fmt_match:
        divisor = 10 ** int(fmt_match.group(2))
    else:
        all_coords = re.findall(r'X(-?\d+)Y(-?\d+)', content)
        sample = max([abs(int(x)) for x, y in all_coords], default=0)
        divisor = 100000 if sample > 1000000 else 100 if sample > 10000 else 10

    x_coords = []
    y_coords = []
    for line in content.splitlines():
        if 'D01' in line or 'D02' in line or 'D03' in line:
            match = re.search(r'X(-?\d+)Y(-?\d+)', line)
            if match:
                x_coords.append(int(match.group(1)) / divisor)
                y_coords.append(int(match.group(2)) / divisor)

    if not x_coords:
        return None, None

    width  = round(max(x_coords) - min(x_coords), 2)
    height = round(max(y_coords) - min(y_coords), 2)
    return width, height


@app.route('/analyze', methods=['POST'])
def analyze():
    print('--- Request received ---')
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        zip_path = 'uploaded.zip'
        file.save(zip_path)
        print(f'File saved: {file.filename}')

        width, height = get_dimensions(zip_path)
        print(f'Dimensions: {width} x {height} mm')

        if width is None:
            return jsonify({'error': 'Could not read .GKO outline file'}), 400

        return jsonify({'width': width, 'height': height})

    except Exception as e:
        print(f'ERROR: {e}')
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

