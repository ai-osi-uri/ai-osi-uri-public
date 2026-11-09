"""Remove the small framing jump at each clip junction of film.mp4.

For every junction (every SEG frames) we estimate the affine warp that maps the
last frame of clip A onto the first frame of clip B, then over the last RAMP
frames of clip A we ease the camera framing (and colour balance) toward that
warp. The result is a physical-looking camera correction, not a cross-fade.
Usage: python3 align_film.py film.mp4 out.mp4
"""
import subprocess, sys
import numpy as np, cv2

src, dst = sys.argv[1], sys.argv[2]
W, H, SEG, RAMP = 1280, 712, 120, 30   # must match build_film.sh output; SEG = frames per clip after trimming

def read_all(path):
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)

# pass 1: grab junction frames
need = set()
total = int(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip())
juncs = [j * SEG for j in range(1, total // SEG + 1)]           # first frame of next clip (last one = loop back to 0)
for j in juncs:
    need.update({j - 1, j % total})
store = {}
for i, f in enumerate(read_all(src)):
    if i in need:
        store[i] = f.copy()

def estimate(a, b):
    ga = cv2.cvtColor(cv2.resize(a, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(cv2.resize(b, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    M = np.eye(2, 3, dtype=np.float32)
    try:
        _, M = cv2.findTransformECC(gb, ga, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error:
        M = np.eye(2, 3, dtype=np.float32)
    M[:, 2] *= 2  # back to full resolution
    # colour: per-channel mean/std transfer A -> B
    am, asd = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-3
    bm, bsd = b.reshape(-1, 3).mean(0), b.reshape(-1, 3).std(0) + 1e-3
    return M, (am, asd, bm, bsd)

plans = {}
for j in juncs:
    a, b = store[j - 1], store[j % total]
    M, col = estimate(a, b)
    warped = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    before = np.abs(a.astype(float) - b).mean(); after = np.abs(warped.astype(float) - b).mean()
    print(f'junction@{j}: diff {before:.1f} -> {after:.1f}')
    if after >= before:          # warp did not help: leave this junction untouched
        continue
    plans[j] = (M, col)

def ease(t):
    return t * t * (3 - 2 * t)

enc = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '24', '-i', '-',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '27', '-g', '48', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst], stdin=subprocess.PIPE)
I = np.eye(2, 3, dtype=np.float32)
for i, f in enumerate(read_all(src)):
    out = f
    for j, (M, (am, asd, bm, bsd)) in plans.items():
        if j - RAMP <= i < j:
            t = ease((i - (j - RAMP) + 1) / RAMP)
            Mt = (I + (M - I) * t).astype(np.float32)
            out = cv2.warpAffine(f, Mt, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
            x = out.reshape(-1, 3).astype(np.float32)
            tgt = (x - am) / asd * bsd + bm
            out = np.clip(x + (tgt - x) * t, 0, 255).astype(np.uint8).reshape(H, W, 3)
    enc.stdin.write(np.ascontiguousarray(out).tobytes())
enc.stdin.close(); enc.wait()
