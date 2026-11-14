import base64, sys, os
src = 'src'; out = sys.argv[1] if len(sys.argv) > 1 else 'dist/index.html'
html = open(f'{src}/index.html').read()
b64 = base64.b64encode(open('manok.glb','rb').read()).decode()
html = html.replace('/*__MODEL__*/', 'window.MANOK_GLB = "data:model/gltf-binary;base64,' + b64 + '";')
for k, f in (('SIM','sim.js'),('BOT','bot.js'),('GAME','game.js')):
    js = open(f'{src}/{f}').read()
    assert '</script' not in js
    html = html.replace(f'/*__{k}__*/', js)
if '--local' in sys.argv:
    html = html.replace('https://cdn.jsdelivr.net/npm/babylonjs@7.54.3/babylon.js', 'node_modules/babylonjs/babylon.js')
    html = html.replace('https://cdn.jsdelivr.net/npm/babylonjs-loaders@7.54.3/babylonjs.loaders.min.js', 'node_modules/babylonjs-loaders/babylonjs.loaders.min.js')
    html = html.replace('<link href="https://fonts.googleapis.com/css2?family=Bungee&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">', '')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w').write(html); print(out, len(html)//1024, 'KB')
