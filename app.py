from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

# User Agent Rotation (To prevent blocking)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.pinterest.com/"
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-media', methods=['POST'])
def get_media():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({'error': 'URL missing'}), 400

    try:
        # Request with updated headers
        response = requests.get(url, headers=HEADERS, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        media_url = None
        media_type = 'image'
        
        # 1. Try Meta Tags
        og_video = soup.find("meta", property="og:video")
        og_image = soup.find("meta", property="og:image")
        
        if og_video:
            media_url = og_video['content']
            media_type = 'video'
        elif og_image:
            media_url = og_image['content']
            media_type = 'image'
        
        # 2. Fallback: Try JSON data inside scripts (More reliable for Pinterest)
        if not media_url:
            video_tag = soup.find("video")
            if video_tag and video_tag.get('src'):
                media_url = video_tag['src']
                media_type = 'video'

        if media_url:
            # Fix m3u8 links (Convert to mp4)
            if 'm3u8' in media_url:
                media_url = media_url.replace('hls', '720p').replace('.m3u8', '.mp4')
            
            # Add a timestamp to URL to prevent caching
            return jsonify({'success': True, 'type': media_type, 'url': media_url})
        
        return jsonify({'error': 'Media not found.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-download')
def proxy_download():
    video_url = request.args.get('url')
    if not video_url: return "No URL", 400

    try:
        # Stream Content
        req = requests.get(video_url, stream=True, headers=HEADERS)
        
        # Headers setup for forcing download
        headers = {
            'Content-Type': 'video/mp4',
            'Content-Disposition': f'attachment; filename="PinDown_{int(time.time())}.mp4"',
            'Cache-Control': 'no-cache, no-store, must-revalidate', # Prevents caching
            'Pragma': 'no-cache',
            'Expires': '0'
        }

        # Pass content length if available
        total_size = req.headers.get('content-length')
        if total_size:
            headers['Content-Length'] = total_size

        return Response(stream_with_context(req.iter_content(chunk_size=8192)), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
