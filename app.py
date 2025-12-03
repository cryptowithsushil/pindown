from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)

# Pinterest Browser Headers
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
        # 1. Page Fetch karein
        response = requests.get(url, headers=HEADERS, allow_redirects=True)
        html_content = response.text
        
        video_url = None
        
        # METHOD 1: Regex se sidha 720p.mp4 dhundna (Sabse Best Tarika)
        # Ye pure page me .mp4 link dhundega
        found_urls = re.findall(r'https://[^"]+?/720p/[^"]+?\.mp4', html_content)
        
        if found_urls:
            video_url = found_urls[0] # Sabse pehla link utha lo
        
        # METHOD 2: Agar 720p nahi mila, to normal mp4 dhundo
        if not video_url:
            found_urls = re.findall(r'https://[^"]+?\.mp4', html_content)
            if found_urls:
                video_url = found_urls[0]

        # METHOD 3: Fallback to Meta Tags (Video or Image)
        if not video_url:
            soup = BeautifulSoup(html_content, 'html.parser')
            og_video = soup.find("meta", property="og:video")
            og_image = soup.find("meta", property="og:image")
            
            if og_video:
                video_url = og_video['content']
            elif og_image:
                # Agar video nahi hai to photo dikha dega
                return jsonify({'success': True, 'type': 'image', 'url': og_image['content']})

        if video_url:
            # Final check: Ensure it is NOT an m3u8 file masked as mp4
            if '.m3u8' in video_url:
                # Force replace to mp4 structure if regex failed
                video_url = video_url.replace('/hls/', '/720p/').replace('.m3u8', '.mp4')

            return jsonify({'success': True, 'type': 'video', 'url': video_url})
        
        return jsonify({'error': 'Video not found inside page.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-download')
def proxy_download():
    video_url = request.args.get('url')
    if not video_url: return "No URL", 400

    try:
        # Request the video stream
        req = requests.get(video_url, stream=True, headers=HEADERS)
        
        # Check if the link is actually working (Status 200)
        if req.status_code != 200:
            return "Error: Video link expired or blocked", 400

        # File Size Pata Karein
        total_size = req.headers.get('content-length')
        
        # Filename Generation
        filename = f"PinDown_Video_{int(time.time())}.mp4"

        headers = {
            'Content-Type': 'video/mp4',
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
        if total_size:
            headers['Content-Length'] = total_size

        return Response(stream_with_context(req.iter_content(chunk_size=1024*1024)), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
