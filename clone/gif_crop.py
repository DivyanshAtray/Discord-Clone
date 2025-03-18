from flask import Blueprint, request, jsonify
from PIL import Image
import io
import base64

# Create a Flask blueprint for GIF cropping
gif_crop_bp = Blueprint('gif_crop', __name__)

def crop_gif_in_memory(gif_data, crop_x, crop_y, crop_width, crop_height):
    try:
        # Load GIF from bytes
        gif = Image.open(io.BytesIO(gif_data))
        frames = []
        durations = []

        # Iterate through all frames
        for frame in range(gif.n_frames):
            gif.seek(frame)
            new_frame = Image.new('RGBA', gif.size)
            new_frame.paste(gif)
            # Crop the frame
            cropped_frame = new_frame.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
            frames.append(cropped_frame)
            durations.append(gif.info.get('duration', 100))

        # Create a bytes buffer for the new GIF
        output_buffer = io.BytesIO()
        frames[0].save(
            output_buffer,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0
        )
        output_buffer.seek(0)
        return output_buffer.read()
    except Exception as e:
        print(f"Error cropping GIF: {e}")
        return None

@gif_crop_bp.route('/crop-gif', methods=['POST'])
def crop_gif_route():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'})

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    if file:
        # Read GIF data into memory
        gif_data = file.read()

        crop_x = float(request.form.get('crop_x', 0))
        crop_y = float(request.form.get('crop_y', 0))
        crop_width = float(request.form.get('crop_width', 0))
        crop_height = float(request.form.get('crop_height', 0))

        # Basic validation (ensure crop dimensions are positive)
        crop_x = max(0, crop_x)
        crop_y = max(0, crop_y)
        crop_width = max(1, crop_width)
        crop_height = max(1, crop_height)

        # Crop the GIF in memory
        cropped_gif_data = crop_gif_in_memory(gif_data, crop_x, crop_y, crop_width, crop_height)
        if cropped_gif_data:
            # Encode the cropped GIF as base64 for the response
            cropped_gif_base64 = base64.b64encode(cropped_gif_data).decode('utf-8')
            return jsonify({
                'success': True,
                'base64': cropped_gif_base64,  # Return base64 string
                'filename': f'cropped_{file.filename}'
            })
        else:
            return jsonify({'success': False, 'error': 'Error processing GIF'})

    return jsonify({'success': False, 'error': 'Invalid file'})