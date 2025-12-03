from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

# Pinterest ko lagna chahiye ki hum browser hain
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
        # 1. Page Fetch Karein
        response = requests.get(url, headers=HEADERS, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        media_url = None
        media_type = 'image'
        
        # 2. Meta Tags check karein
        og_video = soup.find("meta", property="og:video")
        og_image = soup.find("meta", property="og:image")
        
        if og_video:
            raw_url = og_video['content']
            media_type = 'video'
            
            # --- SMART LINK CONVERTER (FIXED) ---
            if 'm3u8' in raw_url:
                # HLS link ko MP4 me badalne ki koshish (High Quality)
                possible_mp4 = raw_url.replace('/hls/', '/720p/').replace('.m3u8', '.mp4')
                
                # Check karein ki kya ye 720p link zinda hai?
                check = requests.head(possible_mp4, headers=HEADERS)
                if check.status_code == 200:
                    media_url = possible_mp4
                else:
                    # Agar 720p nahi mila, to original m3u8 hi bhej do (browser play kar lega)
                    # Ya fir fallback try karo
                    media_url = raw_url
            else:
                media_url = raw_url

        elif og_image:
            media_url = og_image['content']
            media_type = 'image'
        
        # 3. Fallback: Agar meta tag se nahi mila to <video> tag dhundo
        if not media_url:
            video_tag = soup.find("video")
            if video_tag and video_tag.get('src'):
                media_url = video_tag['src']
                media_type = 'video'

        if media_url:
            return jsonify({'success': True, 'type': media_type, 'url': media_url})
        
        return jsonify({'error': 'Media not found.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-download')
def proxy_download():
    video_url = request.args.get('url')
    if not video_url: return "No URL", 400

    try:
        # Stream=True zaroori hai badi files ke liye
        req = requests.get(video_url, stream=True, headers=HEADERS)
        
        # Check karein ki video sach me aa raha hai ya error page
        if req.status_code != 200:
            return "Failed to fetch video from Pinterest", 400

        total_size = req.headers.get('content-length')
        
        # Unique Filename generate karein taaki purani file replace na ho
        filename = f"PinDown_{int(time.time())}.mp4"

        headers = {
            'Content-Type': 'video/mp4',
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
        if total_size:
            headers['Content-Length'] = total_size

        return Response(stream_with_context(req.iter_content(chunk_size=4096)), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
