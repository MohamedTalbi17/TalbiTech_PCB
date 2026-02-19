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

    files = os.listdir(extract_folder)

    # count layers
    top    = any(f.upper().endswith('.GTL') for f in files)
    bottom = any(f.upper().endswith('.GBL') for f in files)
    layers = 2 if (top and bottom) else 1

    # find outline
    outline_file = None
    for filename in files:
        if filename.upper().endswith('.GKO'):
            outline_file = os.path.join(extract_folder, filename)
            break

    if not outline_file:
        return None, None, layers, 'no_outline'

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
        return None, None, layers, 'no_coords'

    width  = round(max(x_coords) - min(x_coords), 2)
    height = round(max(y_coords) - min(y_coords), 2)
    return width, height, layers, None


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']

        if not file.filename.lower().endswith('.zip'):
            return jsonify({'error': 'not_zip'}), 400

        zip_path = 'uploaded.zip'
        file.save(zip_path)

        width, height, layers, err = get_dimensions(zip_path)

        if err:
            return jsonify({'error': err}), 400

        return jsonify({'width': width, 'height': height, 'layers': layers})

    except Exception as e:
        print(f'ERROR: {e}')
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

