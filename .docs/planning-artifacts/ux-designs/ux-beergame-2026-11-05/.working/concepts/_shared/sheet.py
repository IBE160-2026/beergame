import subprocess, sys, pathlib
root = pathlib.Path('.')
out = pathlib.Path(sys.argv[1]); out.mkdir(exist_ok=True, parents=True)
W, H = 760, 560
for stem in sys.argv[2:]:
    pngs = sorted(root.glob(f'[0-9][0-9]-*/_png/{stem}.png'))
    args = ['ffmpeg', '-y', '-loglevel', 'error']
    for p in pngs:
        args += ['-i', str(p)]
    f = ''.join(f'[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:0:0:color=gray[v{i}];' for i in range(len(pngs)))
    layout = '|'.join(f'{(i % 4) * W}_{(i // 4) * H}' for i in range(len(pngs)))
    f += ''.join(f'[v{i}]' for i in range(len(pngs))) + f'xstack=inputs={len(pngs)}:layout={layout}:fill=gray'
    subprocess.run(args + ['-filter_complex', f, str(out / f'{stem}.jpg')], check=True)
    print(out / f'{stem}.jpg')
