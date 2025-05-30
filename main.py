import asyncio
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, Response, send_file
from loguru import logger

from gr.fm_reception import fm_reception

app = Flask(__name__)

# global configuration
OUTPUT_DIR = Path("./tmp/public")
WAV_FILE = Path("./tmp/sound.wav")
M3U_FILE = OUTPUT_DIR / "stream.m3u8"


@app.route("/")
def serve_playlist_m3u():
    """Return playlist M3U file"""
    playlist_content = """#EXTM3U
#EXTINF:0,Tokyo FM
http://host.docker.internal:8080/stream.m3u8
"""
    return Response(playlist_content, mimetype="audio/x-mpegurl")


@app.route("/stream.m3u8")
def serve_hls_stream():
    """Return HLS stream M3U8 file"""
    if M3U_FILE.exists():
        return send_file(M3U_FILE, mimetype="application/vnd.apple.mpegurl")
    else:
        return Response("HLS stream not found", status=404)


@app.route("/<path:filename>.ts")
def serve_segment(filename):
    """Return HLS segment file"""
    segment_path = OUTPUT_DIR / f"{filename}.ts"
    if segment_path.exists():
        return send_file(segment_path, mimetype="video/mp2t")
    else:
        return Response("Segment not found", status=404)


async def run_fm_reception():
    """Execute the FM reception flow graph in a separate thread"""
    logger.info("Starting FM reception flow graph...")

    # Initialize the flow graph
    tb = fm_reception()

    def run_flowgraph():
        try:
            tb.start()
            tb.flowgraph_started.set()
            logger.trace("FM reception flow graph started successfully")
            tb.wait()
        except Exception as e:
            logger.error(f"Error in flow graph: {e}")
        finally:
            if tb.started():
                tb.stop()
                tb.wait()

    # Start the flow graph in a separate thread
    thread = threading.Thread(target=run_flowgraph)
    thread.daemon = True
    thread.start()

    # フローグラフが開始されるまで待機
    await asyncio.sleep(0.1)
    while not tb.flowgraph_started.is_set():
        await asyncio.sleep(0.1)

    return tb, thread


async def monitor_and_convert_wav():
    """Monitor the WAV file and convert it to HLS format using FFmpeg"""
    logger.info("Starting FFmpeg file conversion...")

    # Ensure the output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ffmpeg_process = None

    try:
        while True:
            # When the WAV file is created or modified, start FFmpeg conversion
            if WAV_FILE.exists() and WAV_FILE.stat().st_size > 0:
                # Kill any existing FFmpeg process
                if ffmpeg_process and ffmpeg_process.poll() is None:
                    ffmpeg_process.terminate()
                    ffmpeg_process.wait()

                # FFmpeg command
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-f",
                    "wav",
                    "-re",  # realtime mode
                    "-i",
                    str(WAV_FILE),
                    "-c:a",
                    "aac",  # codec
                    "-b:a",
                    "48k",  # bitrate
                    "-f",
                    "hls",
                    "-hls_time",
                    "10",  # segment duration (seconds)
                    "-hls_list_size",
                    "10",  # maximum number of segments in the playlist
                    "-hls_flags",
                    "delete_segments",  # delete old segments
                    "-hls_segment_filename",
                    str(OUTPUT_DIR / "segment_%03d.ts"),
                    str(M3U_FILE),
                    "-y",  # overwrite output files
                ]

                # Start FFmpeg process
                ffmpeg_process = subprocess.Popen(
                    ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                logger.trace("Started FFmpeg process for conversion")
                logger.trace(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

                # Monitor the FFmpeg process
                while ffmpeg_process.poll() is None:
                    await asyncio.sleep(5)
                    if not WAV_FILE.exists():
                        logger.warning("WAV file disappeared, stopping FFmpeg")
                        ffmpeg_process.terminate()
                        break

                # Check if FFmpeg has completed
                if ffmpeg_process.poll() is not None:
                    stdout, stderr = ffmpeg_process.communicate()
                    if ffmpeg_process.returncode != 0:
                        logger.error(f"FFMpeg error: {stderr.decode()}")
                    else:
                        logger.trace("FFmpeg conversion completed successfully")

            await asyncio.sleep(2)  # Wait before checking again

    except Exception as e:
        logger.error(f"Error in WAV monitoring: {e}")
    finally:
        if ffmpeg_process and ffmpeg_process.poll() is None:
            ffmpeg_process.terminate()
            ffmpeg_process.wait()


def run_flask_server():
    """Run the Flask HTTP server"""
    logger.info("Starting Flask HTTP server...")
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
    logger.trace("Flask server started successfully")


async def main():
    # log configuration
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    logger.add(sys.stderr, level="ERROR")

    logger.info("Starting sdr-m3u-tuner...")

    try:
        # Start FM reception in a separate thread
        tb, fm_thread = await run_fm_reception()

        # Start WAV file monitoring and conversion
        conversion_task = asyncio.create_task(monitor_and_convert_wav())

        # Start HTTP server in a separate thread
        flask_thread = threading.Thread(target=run_flask_server)
        flask_thread.daemon = True
        flask_thread.start()

        # main loop
        while fm_thread.is_alive():
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nStopping all services...")
        if "tb" in locals():
            tb.stop()
            tb.wait()
        if "conversion_task" in locals():
            conversion_task.cancel()
    except Exception as e:
        logger.error(f"Error: {e}")
        if "tb" in locals():
            tb.stop()
            tb.wait()


if __name__ == "__main__":
    asyncio.run(main())
