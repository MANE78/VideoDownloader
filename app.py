from flask import Flask, request, send_file, render_template_string
import yt_dlp
import os
import logging
import socket

app = Flask(__name__)

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

HOME_PAGE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Downloader Pro</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background: #ecf0f1; }
        h1 { color: #34495e; }
        .container { max-width: 700px; margin: 0 auto; }
        input[type="text"] { padding: 12px; width: 80%; border: 1px solid #bdc3c7; border-radius: 5px; }
        select { padding: 12px; margin: 10px; width: 50%; border-radius: 5px; }
        button { padding: 12px 30px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #2980b9; }
        .message { margin: 10px; padding: 10px; border-radius: 5px; }
        .error { background: #f9ebeb; color: #e74c3c; }
        .success { background: #e9f7ef; color: #27ae60; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Video Downloader Pro</h1>
        <p>أدخل رابط الفيديو لبدء التنزيل</p>
        <form method="POST" action="/download">
            <input type="text" name="url" placeholder="أدخل رابط الفيديو أو قائمة التشغيل" required><br>
            <select name="format">
                <option value="best">أفضل جودة فيديو (مع الصوت)</option>
                <option value="720p">720p (مع الصوت)</option>
                <option value="1080p">1080p (مع الصوت)</option>
                <option value="mp3">صوت فقط (MP3)</option>
                <option value="playlist">تحميل قائمة تشغيل (مع الصوت)</option>
            </select><br>
            <button type="submit">تنزيل</button>
        </form>
        {% if message %}
            <div class="message {{ status }}">{{ message }}</div>
        {% endif %}
    </div>
</body>
</html>
'''

def download_content(url, options):
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            logging.info(f"تم تحميل الملف: {filename}")
            return filename
    except Exception as e:
        logging.error(f"خطأ أثناء التحميل: {str(e)}")
        raise

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

@app.route('/')
def home():
    return render_template_string(HOME_PAGE, message=None, status=None)

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    format_choice = request.form['format']

    if format_choice == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'outtmpl': 'downloads/audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    elif format_choice == "playlist":
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': 'downloads/%(playlist_title)s/%(title)s.%(ext)s',
            'yes_playlist': True,
        }
    else:
        format_map = {
            'best': 'bestvideo+bestaudio/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best'
        }
        ydl_opts = {
            'format': format_map.get(format_choice, 'bestvideo+bestaudio/best'),
            'merge_output_format': 'mp4',
            'outtmpl': 'downloads/video.%(ext)s',
        }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        output_file = download_content(url, ydl_opts)

        if format_choice == "playlist":
            import shutil
            shutil.make_archive('playlist', 'zip', 'downloads')
            return send_file('playlist.zip', as_attachment=True)
        elif os.path.exists(output_file):
            return send_file(output_file, as_attachment=True)
        else:
            return render_template_string(HOME_PAGE, message="فشل التحميل: الملف غير موجود بعد التحميل", status="error")

    except Exception as e:
        return render_template_string(HOME_PAGE, message=f"فشل التحميل: {str(e)}", status="error")

@app.after_request
def cleanup(response):
    for file in ['downloads/video.mp4', 'downloads/audio.mp3', 'playlist.zip']:
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
    if os.path.exists('downloads'):
        import shutil
        shutil.rmtree('downloads', ignore_errors=True)
    return response

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))  # للتوافق مع Render
    local_ip = get_local_ip()
    print(f"السيرفر يعمل على: http://localhost:{port} أو http://{local_ip}:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)
