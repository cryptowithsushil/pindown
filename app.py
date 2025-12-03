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
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. VIDEO CHECK
        video_url = None
        
        # Regex se MP4 dhundo
        found_mp4 = re.findall(r'https://[^"]+?/720p/[^"]+?\.mp4', html_content)
        if found_mp4: video_url = found_mp4[0]
        
        if not video_url:
            found_generic = re.findall(r'https://[^"]+?\.mp4', html_content)
            if found_generic: video_url = found_generic[0]

        if not video_url:
            og_video = soup.find("meta", property="og:video")
            if og_video: video_url = og_video['content']

        # --- SCENARIO A: VIDEO FOUND ---
        if video_url:
            # Cleanup m3u8
            if '.m3u8' in video_url:
                video_url = video_url.replace('/hls/', '/720p/').replace('.m3u8', '.mp4')

            # FORCE GENERATE QUALITIES (1080p, 720p, 480p)
            qualities = []
            
            # Pinterest standard format check (.../720p/...)
            if '/720p/' in video_url:
                # Hum check nahi karenge, bas link bana denge (Force Add)
                resolutions = ['1080p', '720p', '480p']
                for res in resolutions:
                    # Naya URL banao
                    force_url = video_url.replace('/720p/', f'/{res}/')
                    qualities.append({'label': f'{res} HD', 'url': force_url})
            else:
                # Agar URL pattern alag hai, to bas original dikhao
                qualities.append({'label': 'Standard Quality', 'url': video_url})

            return jsonify({
                'success': True, 
                'type': 'video', 
                'qualities': qualities,
                'thumbnail': ''
            })

        # --- SCENARIO B: IMAGE FOUND ---
        og_image = soup.find("meta", property="og:image")
        if og_image:
            return jsonify({
                'success': True, 
                'type': 'image', 
                'url': og_image['content']
            })

        return jsonify({'error': 'Media not found.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-download')
def proxy_download():
    file_url = request.args.get('url')
    file_type = request.args.get('type')
    
    if not file_url: return "No URL", 400

    try:
        # Stream request
        req = requests.get(file_url, stream=True, headers=HEADERS)
        
        # Agar 1080p nahi mila (403/404), to user ko batana padega
        if req.status_code != 200:
            return "Selected quality not available. Try another.", 404

        if file_type == 'image':
            ext = 'jpg'
            content_type = 'image/jpeg'
        else:
            ext = 'mp4'
            content_type = 'video/mp4'
        
        filename = f"PinDown_{int(time.time())}.{ext}"

        headers = {
            'Content-Type': content_type,
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': req.headers.get('content-length')
        }

        return Response(stream_with_context(req.iter_content(chunk_size=4096)), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
