from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
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
        response = requests.get(url, headers=HEADERS, allow_redirects=True)
        html_content = response.text
        
        video_url = None
        
        # 1. Video Search (Priority)
        found_urls = re.findall(r'https://[^"]+?/720p/[^"]+?\.mp4', html_content)
        if found_urls: video_url = found_urls[0]
        
        if not video_url:
            found_urls = re.findall(r'https://[^"]+?\.mp4', html_content)
            if found_urls: video_url = found_urls[0]

        # 2. Meta Tag Fallback
        soup = BeautifulSoup(html_content, 'html.parser')
        og_video = soup.find("meta", property="og:video")
        og_image = soup.find("meta", property="og:image")

        if not video_url and og_video:
            video_url = og_video['content']

        # 3. Final Decision: Video or Image?
        if video_url:
            if '.m3u8' in video_url:
                video_url = video_url.replace('/hls/', '/720p/').replace('.m3u8', '.mp4')
            return jsonify({'success': True, 'type': 'video', 'url': video_url})
        
        elif og_image:
            # Agar video nahi mila, to Image return karo
            return jsonify({'success': True, 'type': 'image', 'url': og_image['content']})

        return jsonify({'error': 'Media not found.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-download')
def proxy_download():
    media_url = request.args.get('url')
    media_type = request.args.get('type') # Video ya Image?
    
    if not media_url: return "No URL", 400

    try:
        req = requests.get(media_url, stream=True, headers=HEADERS)
        
        if req.status_code != 200:
            return "Error fetching media", 400

        total_size = req.headers.get('content-length')
        
        # Extension decide karo based on type
        ext = 'mp4' if media_type == 'video' else 'jpg'
        content_type = 'video/mp4' if media_type == 'video' else 'image/jpeg'
        
        filename = f"PinDown_{int(time.time())}.{ext}"

        headers = {
            'Content-Type': content_type,
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
        if total_size:
            headers['Content-Length'] = total_size

        return Response(stream_with_context(req.iter_content(chunk_size=1024*1024)), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
