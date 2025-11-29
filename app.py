from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Browser User-Agent (Taaki Pinterest block na kare)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-media', methods=['POST'])
def get_media():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'Please provide a URL'}), 400

    try:
        # Pinterest URL se content lana
        response = requests.get(url, headers=HEADERS, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        media_url = None
        media_type = 'image'
        
        # Video/Image Link dhoondna
        og_video = soup.find("meta", property="og:video")
        og_image = soup.find("meta", property="og:image")
        
        if og_video:
            media_url = og_video['content']
            media_type = 'video'
        elif og_image:
            media_url = og_image['content']
            media_type = 'image'
        
        if media_url:
            return jsonify({'success': True, 'type': media_type, 'url': media_url})
        else:
            return jsonify({'error': 'Media not found. Try checking the link.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Download Progress Route
@app.route('/proxy-download')
def proxy_download():
    video_url = request.args.get('url')
    if not video_url: return "No URL", 400
    try:
        req = requests.get(video_url, stream=True, headers=HEADERS)
        headers = {
            'Content-Type': req.headers.get('Content-Type'),
            'Content-Disposition': 'attachment; filename="pinterest_video.mp4"',
            'Content-Length': req.headers.get('Content-Length')
        }
        return Response(stream_with_context(req.iter_content(chunk_size=4096)), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)