"""Find dissolves (two pictures overlapping) and hard cuts in a clip or a joined film.

A frame-to-frame difference check cannot see a dissolve: every step is small.
What gives a dissolve away is that the middle frame is almost exactly a mix of
the frame before and the frame after, while those two are very different
pictures. A real camera move does not behave like that (a mix of two camera
positions shows ghosting that the real middle frame does not have).

Usage: python3 find_dissolves.py film.mp4 [--sheet out.jpg]
Exit code 1 when anything is found. Thresholds are starting values; see
references/observations.md for the conditions they were measured under.
"""
import subprocess, sys
import numpy as np

W, H, FPS = 160, 90, 12          # analysis size and rate
KS = (6, 12, 18)                 # look 0.5s / 1s / 1.5s before and after (slow dissolves need the wide one)
FAR, MIX, CUT = 22.0, 0.42, 6.0  # "different pictures" / "explained by a mix" / "jump vs. usual step"


def frames(path):
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', path, '-vf', f'fps={FPS},scale={W}:{H}',
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
    raw = p.stdout.read()
    n = len(raw) // (W * H)
    return np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)


def main():
    path = sys.argv[1]
    sheet = sys.argv[sys.argv.index('--sheet') + 1] if '--sheet' in sys.argv else None
    f = frames(path)
    n = len(f)
    hits = []
    step = np.abs(f[1:] - f[:-1]).mean(axis=(1, 2))
    usual = float(np.median(step)) + 1e-6
    for i in np.where(step > max(CUT * usual, 12.0))[0]:
        hits.append((float(i + 1) / FPS, 'cut', float(step[i] / usual)))
    best = {}
    for K in KS:
        for m in range(K, n - K):
            a, b, c = f[m - K], f[m + K], f[m]
            far = float(np.abs(a - b).mean())
            if far < FAR:
                continue
            d = (a - b).ravel()
            alpha = float(np.clip(np.dot((c - b).ravel(), d) / (np.dot(d, d) + 1e-6), 0, 1))
            if not 0.2 < alpha < 0.8:
                continue
            left = float(np.abs(c - (alpha * a + (1 - alpha) * b)).mean())
            if left / far < MIX:
                best[m] = min(best.get(m, 9), left / far)
    hits += [(m / FPS, 'dissolve', v) for m, v in best.items()]
    # merge neighbours into spans
    spans = []
    for t, kind, v in sorted(hits):
        if spans and spans[-1][2] == kind and t - spans[-1][1] <= 0.5:
            spans[-1][1] = t
            spans[-1][3] = min(spans[-1][3], v) if kind == 'dissolve' else max(spans[-1][3], v)
        else:
            spans.append([t, t, kind, v])
    for s in spans:
        print(f'{s[2]:8s} {s[0]:6.2f}s - {s[1]:6.2f}s  score={s[3]:.2f}')
    print(f'{len(spans)} found in {n / FPS:.1f}s')
    if sheet and spans:
        parts = []
        for i, s in enumerate(spans[:12]):
            mid = (s[0] + s[1]) / 2
            out = f'/tmp/_fd_{i}.jpg'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', f'{max(mid - 0.6, 0):.2f}', '-t', '1.2', '-i', path,
                            '-vf', 'fps=5,scale=320:-2,tile=6x1', '-frames:v', '1', out], check=True)
            parts += ['-i', out]
        k = len(parts) // 2
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *parts, '-filter_complex',
                        ''.join(f'[{i}:v]' for i in range(k)) + f'vstack=inputs={k}' if k > 1 else '[0:v]copy',
                        '-frames:v', '1', sheet], check=True)
        print('sheet:', sheet)
    sys.exit(1 if spans else 0)


if __name__ == '__main__':
    main()
